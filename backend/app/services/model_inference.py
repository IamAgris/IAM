"""Unified real-model inference for chat and autonomy (OD independence).

One decision path decides whether live inference is available:
  1. hosted provider keys -> LiteLLM gateway (existing free-only policy);
  2. opted-in Ollama -> its OpenAI-compatible endpoint (no key, local);
  3. otherwise -> explicit offline status, never fabricated reasoning.

No API key is ever returned by these helpers.
"""

from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
import loguru

from app.core.config import settings
from app.services import serving_model

logger = loguru.logger

HOSTED_PROVIDERS = (
    ("nvidia", "nvidia_api_key"),
    ("dashscope", "dashscope_api_key"),
    ("openai", "openai_api_key"),
    ("anthropic", "anthropic_api_key"),
)


class InferenceUnavailable(RuntimeError):
    """Raised when no provider is configured or reachable."""


@dataclass(frozen=True)
class InferenceStatus:
    available: bool
    mode: str  # hosted | ollama | offline
    model: Optional[str]
    providers: List[Dict[str, Any]]
    reason: str
    primary: str = ""  # IAM's active primary model (alias), before resolution

    def as_dict(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "mode": self.mode,
            "model": self.model,
            "providers": self.providers,
            "reason": self.reason,
            "primary": self.primary,
            "claim": "live_inference_only_when_reported_available",
        }


class InferenceService:
    """Resolve and use the best available real model for IAM."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def hosted_providers(self) -> List[Dict[str, Any]]:
        return [
            {"name": name, "configured": bool(getattr(settings, field, None))}
            for name, field in HOSTED_PROVIDERS
        ]

    async def _ollama_models(self) -> List[str]:
        """Return locally available model tags, or [] when Ollama is unavailable."""
        if not settings.ollama_enabled:
            return []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
            if response.status_code != 200:
                return []
            return [
                str(model.get("name") or model.get("model"))
                for model in response.json().get("models", [])
                if model.get("name") or model.get("model")
            ]
        except httpx.HTTPError as exc:
            logger.debug(f"Ollama unavailable: {exc}")
            return []

    @staticmethod
    def _is_local_alias(model: str) -> bool:
        """True when the name refers to IAM's primary local model, not a hosted specialist."""
        return (
            model == settings.iam_primary_model
            or model == settings.iam_primary_local_tag
            or model.startswith("local-")
        )

    def _local_target(self, model: str, local_models: List[str]) -> Optional[str]:
        """Return the concrete local tag only when that exact model is present.

        Never substitute a different locally installed model for the primary:
        doing so would report one model as the primary while answering with
        another. An unavailable primary falls back to the hosted path instead.
        """
        for alias, tag in (
            (settings.iam_primary_model, settings.iam_primary_local_tag),
            ("local-qwen-3b", "qwen2.5:3b"),  # OD-46 approved secondary local model
        ):
            if model == alias or model == tag:
                return tag if tag in local_models else None
        if model in local_models:
            return model
        return None

    async def _route(
        self, requested: Optional[str]
    ) -> tuple[Optional[str], str, InferenceStatus]:
        """Pick the concrete model id and provider for one request.

        An explicit model id may select a hosted specialist (an API sub-agent).
        With no explicit id, IAM's shared primary model is used for both the
        frontend and backend intelligence.
        """
        status = await self.resolve()
        selected = requested or status.model
        if not selected:
            return None, status.mode, status
        local_models = await self._ollama_models()
        target = self._local_target(selected, local_models) if settings.ollama_enabled else None
        if target:
            return target, "ollama", status
        return selected, "hosted", status

    async def resolve(self) -> InferenceStatus:
        """Resolve the active primary model. The local primary wins when reachable."""
        primary = serving_model.current().model
        hosted = self.hosted_providers()
        configured = [p["name"] for p in hosted if p["configured"]]
        providers = hosted + [
            {
                "name": "ollama",
                "configured": bool(settings.ollama_enabled),
                "enabled": bool(settings.ollama_enabled),
            }
        ]
        local_models = await self._ollama_models()
        local_target = self._local_target(primary, local_models)
        if local_target:
            return InferenceStatus(
                available=True,
                mode="ollama",
                model=local_target,
                providers=providers,
                reason="IAM primary local model is reachable",
                primary=primary,
            )
        if configured:
            # A hosted model is a fallback/sub-agent, never the identity.
            fallback = settings.iam_sdk_default_model if self._is_local_alias(primary) else primary
            reason = (
                "Primary local model unavailable; hosted specialist fallback: "
                + ", ".join(configured)
                if self._is_local_alias(primary)
                else f"Hosted provider key configured: {', '.join(configured)}"
            )
            return InferenceStatus(
                available=True,
                mode="hosted",
                model=fallback,
                providers=providers,
                reason=reason,
                primary=primary,
            )
        detail = (
            "Ollama is enabled but the IAM primary local model was not found"
            if settings.ollama_enabled
            else "No hosted provider key and Ollama is not enabled"
        )
        return InferenceStatus(
            available=False,
            mode="offline",
            model=None,
            providers=providers,
            reason=detail,
            primary=primary,
        )

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Run one real chat completion against the resolved provider."""
        timeout = timeout if timeout is not None else settings.inference_chat_timeout_seconds
        selected, mode, status = await self._route(model)
        if not status.available or not selected:
            raise InferenceUnavailable(status.reason)
        payload: Dict[str, Any] = {
            "model": selected,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if mode == "hosted":
            url = f"{settings.litellm_base_url.rstrip('/')}/chat/completions"
            headers = {"Authorization": f"Bearer {settings.litellm_master_key}"}
        else:
            url = f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"
            headers = {}

        # Reasoning models can spend the whole token budget on internal tokens.
        # Retry once with more headroom when only reasoning_content was returned.
        token_budget = max_tokens
        result: Dict[str, Any] = {}
        for attempt in range(2):
            attempt_payload = dict(payload)
            if token_budget is not None:
                attempt_payload["max_tokens"] = token_budget
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    headers={"Content-Type": "application/json", **headers},
                    json=attempt_payload,
                )
            if response.status_code != 200:
                raise InferenceUnavailable(
                    f"{mode} provider returned {response.status_code}: {response.text[:300]}"
                )
            result = response.json()
            message = (result.get("choices") or [{}])[0].get("message") or {}
            if message.get("content") or not message.get("reasoning_content"):
                break
            if attempt == 0 and token_budget is not None:
                token_budget = min(max(token_budget * 4, 512), 2048)
                continue
            break
        result["iam_inference"] = {
            "mode": mode,
            "model": selected,
            "primary": status.primary,
            "reasoning_retry": token_budget != max_tokens,
        }
        return result

    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Yield SSE-shaped dicts: start / delta / done / error (no raw bytes)."""
        selected, mode, status = await self._route(model)
        if not status.available or not selected:
            yield {"event": "error", "data": {"code": "offline", "message": status.reason}}
            return
        payload: Dict[str, Any] = {
            "model": selected,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if mode == "hosted":
            url = f"{settings.litellm_base_url.rstrip('/')}/chat/completions"
            headers = {"Authorization": f"Bearer {settings.litellm_master_key}"}
        else:
            url = f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"
            headers = {}

        yield {
            "event": "start",
            "data": {"model": selected, "mode": mode, "primary": status.primary},
        }
        try:
            async with httpx.AsyncClient(
                timeout=settings.inference_stream_timeout_seconds
            ) as client:
                async with client.stream(
                    "POST",
                    url,
                    headers={"Content-Type": "application/json", **headers},
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        body = ""
                        async for chunk in response.aiter_text():
                            body += chunk
                        yield {
                            "event": "error",
                            "data": {"code": "provider_error", "message": body[:400]},
                        }
                        return
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        raw = line[5:].strip()
                        if raw == "[DONE]":
                            break
                        try:
                            import json

                            obj = json.loads(raw)
                            delta = obj.get("choices", [{}])[0].get("delta", {})
                            text = delta.get("content")
                            if text:
                                yield {"event": "delta", "data": {"text": text}}
                        except Exception:
                            continue
            yield {"event": "done", "data": {"finish_reason": "stop"}}
        except httpx.HTTPError as exc:
            logger.error(f"Model stream failed: {exc}")
            detail = f"{type(exc).__name__}: {exc}".strip()
            yield {
                "event": "error",
                "data": {
                    "code": "stream_error",
                    "message": detail[:300] or "The model did not return a complete response.",
                },
            }


inference_service = InferenceService()
