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


def _estimate_ram_mb(model: str, mode: str) -> int:
    """Conservative RAM estimate for OD-39 admission, before any provider call."""
    if mode == "hosted":
        # Hosted inference is remote; it occupies no local residency slot.
        return 256
    name = model.lower()
    for marker, estimate in (
        ("70b", 14000), ("32b", 6500), ("14b", 3000), ("9b", 2200),
        ("7b", 1800), ("4b", 1300), ("3b", 1200), ("1b", 800),
    ):
        if marker in name:
            return estimate
    return settings.irwm_target_loaded_ram_mb


# Hosted inference occupies no local residency slot. A separate bounded pool
# protects the shared provider account while keeping the OD-39 local one-resident
# rule intact — parallel sub-agents must not be refused by local RAM admission.
_hosted_slots: Any = None


def _hosted_pool() -> Any:
    global _hosted_slots
    if _hosted_slots is None:
        import asyncio

        _hosted_slots = asyncio.Semaphore(max(1, settings.iam_delegation_max_parallel))
    return _hosted_slots


async def _admit_inference(model: str, mode: str) -> Optional[Dict[str, Any]]:
    """Admit one inference request; hosted calls use the remote pool, not IRWM."""
    if mode == "hosted":
        await _hosted_pool().acquire()
        return {
            "decision": "admit",
            "mode": "hosted",
            "reason": "remote inference; no local residency slot consumed",
        }
    if not settings.irwm_enabled:
        return None
    from app.services.irwm import irwm

    decision = await irwm.admit(
        model,
        _estimate_ram_mb(model, mode),
        context_tokens=settings.irwm_context_tokens,
        task_complexity=3,
    )
    if decision.get("decision") != "admit":
        raise InferenceUnavailable(
            "IRWM admission refused: " + str(decision.get("reason") or decision.get("decision"))
        )
    return decision


async def _release_inference(model: str, mode: Optional[str] = None) -> None:
    if mode == "hosted":
        _hosted_pool().release()
        return
    if not settings.irwm_enabled:
        return
    from app.services.irwm import irwm

    await irwm.release(model)


def _inspect_input(messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """Inspect every message with Aegis before it can reach any provider.

    Returns only finding types and severities — never the raw text — so a
    rejection cannot leak the sensitive content that triggered it.
    """
    if not settings.inference_aegis_enabled:
        return None
    from app.services.aegis import aegis

    for index, message in enumerate(messages or []):
        # System prompts are IAM's own trusted instructions; inspecting them
        # makes safety text such as "never grant yourself permissions" match
        # the self-escalation signature and blocks all reasoning. Untrusted
        # input arrives as user/tool content, including injected context.
        if message.get("role") == "system":
            continue
        content = message.get("content")
        if not isinstance(content, str) or not content:
            continue
        result = aegis.analyze_text(content, source="inference_input")
        if not result.get("safe"):
            return {
                "message_index": index,
                "risk": result.get("risk"),
                "findings": [
                    {"type": item.get("type"), "severity": item.get("severity")}
                    for item in result.get("findings", [])[:10]
                ],
            }
    return None

logger = loguru.logger

HOSTED_PROVIDERS = (
    ("nvidia", "nvidia_api_key"),
    ("dashscope", "dashscope_api_key"),
    ("openai", "openai_api_key"),
    ("anthropic", "anthropic_api_key"),
)


def _provider_for_model(model: str) -> str:
    """Map a hosted model alias/id to its provider for key and usage isolation."""
    name = (model or "").lower()
    if "nvidia" in name or "nemotron" in name:
        return "nvidia"
    if "dashscope" in name or name.startswith("qwen3.5"):
        return "dashscope"
    if "gpt-" in name or "openai" in name:
        return "openai"
    if "claude" in name or "anthropic" in name:
        return "anthropic"
    return "unknown"


@dataclass(frozen=True)
class ProviderCallContext:
    """OD-51 key and usage decision for one hosted request (no secret in logs)."""

    provider: str
    is_paid: bool
    credential: Optional[str]
    key_fingerprint: Optional[str]
    decision: Any = None


class InferenceUnavailable(RuntimeError):
    """Raised when no provider is configured or reachable."""


class InferenceBlocked(InferenceUnavailable):
    """Raised when Aegis refuses untrusted input before any provider call."""


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

    async def _prepare_provider_call(
        self, db: Any, selected: str, mode: str
    ) -> ProviderCallContext:
        """Resolve an authorised key and fail-closed usage decision for a call.

        When no database session is supplied (internal/tests), the legacy
        gateway credential is used and no accounting is claimed. Production
        chat routes always pass a session.
        """
        provider = _provider_for_model(selected)
        if db is None or mode != "hosted":
            return ProviderCallContext(provider, False, None, None)
        from app.services.model_credential_vault import ModelCredentialVault, VaultError
        from app.services.model_policy import (
            PAID_ACTION,
            ModelPolicyDenied,
            is_paid_model,
            require_authorization,
        )
        from app.services.model_usage import ModelUsageService

        is_paid = await is_paid_model(db, selected)
        authority = None
        if is_paid:
            try:
                authority = await require_authorization(db, PAID_ACTION, target_ref=selected)
            except ModelPolicyDenied as exc:
                raise InferenceUnavailable(str(exc)) from exc
        decision = await ModelUsageService(db).preflight(
            model=selected,
            is_paid=is_paid,
            authorization=authority,
        )
        if is_paid and not decision.allowed:
            raise InferenceUnavailable("Usage policy denied: " + decision.reason)
        credential = None
        fingerprint = None
        try:
            row, credential = await ModelCredentialVault(db).resolve(
                provider=provider,
                is_paid=is_paid,
                purpose="specialist" if not is_paid else None,
            )
            fingerprint = str(row.key_fingerprint)
            decision = type(decision)(
                allowed=decision.allowed,
                reason=decision.reason,
                estimated_cost_usd=decision.estimated_cost_usd,
                key_fingerprint=fingerprint,
            )
        except VaultError:
            # No vault key configured: the gateway's configured credential is
            # the sole authorised connection. Never invent a key.
            credential = None
        return ProviderCallContext(provider, is_paid, credential, fingerprint, decision)

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
        db: Any = None,
        governance_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run one real chat completion against the resolved provider."""
        from app.services.iplci.context import resolve_governance_context
        from app.services.iplci.gateway import GovernanceRefusal
        from app.services.iplci.integration import enforce_agent_request

        resolved = resolve_governance_context(governance_context)
        if resolved:
            try:
                await enforce_agent_request(
                    db,
                    action="model.invoke",
                    source_id=resolved["source_id"],
                    agent_id=str(resolved.get("agent_id") or "main"),
                    jurisdiction=resolved.get("jurisdiction"),
                )
            except GovernanceRefusal as exc:
                raise InferenceBlocked(f"IPLCI governance refused provider call: {exc}")
        inspection = _inspect_input(messages)
        if inspection:
            kinds = ", ".join(str(f.get("type")) for f in inspection["findings"])
            raise InferenceBlocked(
                f"Aegis refused inference input ({inspection['risk']}): {kinds}"
            )
        timeout = timeout if timeout is not None else settings.inference_chat_timeout_seconds
        selected, mode, status = await self._route(model)
        if not status.available or not selected:
            raise InferenceUnavailable(status.reason)
        call = await self._prepare_provider_call(db, selected, mode)
        admission = await _admit_inference(selected, mode)
        try:
            result = await self._chat_completion(
                selected,
                mode,
                status,
                messages,
                temperature,
                max_tokens,
                timeout,
                admission,
                gateway_credential=call.credential,
            )
            result.setdefault("iam_inference", {}).update(
                {
                    "provider": call.provider,
                    "key_fingerprint": call.key_fingerprint,
                    "usage_decision": call.decision.as_dict() if call.decision else None,
                }
            )
            if db is not None and mode == "hosted":
                from app.services.model_usage import ModelUsageService

                result["iam_inference"]["usage"] = await ModelUsageService(db).record(
                    model=selected,
                    provider=call.provider,
                    usage=result.get("usage"),
                    is_paid=call.is_paid,
                    decision=call.decision,
                    key_fingerprint=call.key_fingerprint,
                )
            return result
        finally:
            await _release_inference(selected, mode)

    async def _chat_completion(
        self,
        selected: str,
        mode: str,
        status: InferenceStatus,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: Optional[int],
        timeout: float,
        admission: Optional[Dict[str, Any]],
        gateway_credential: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": selected,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        if mode == "hosted":
            url = f"{settings.litellm_base_url.rstrip('/')}/chat/completions"
            # A vault key is an authorised gateway credential for this provider
            # connection. It is used briefly and never logged or returned.
            headers = {
                "Authorization": f"Bearer {gateway_credential or settings.litellm_master_key}"
            }
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
            "irwm": admission,
        }
        return result

    async def stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        db: Any = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Yield SSE-shaped dicts: start / delta / done / error (no raw bytes)."""
        inspection = _inspect_input(messages)
        if inspection:
            yield {
                "event": "error",
                "data": {
                    "code": "security_blocked",
                    "message": "Aegis refused inference input: "
                    + ", ".join(str(f.get("type")) for f in inspection["findings"])[:300],
                },
            }
            return
        selected, mode, status = await self._route(model)
        if not status.available or not selected:
            yield {"event": "error", "data": {"code": "offline", "message": status.reason}}
            return
        try:
            call = await self._prepare_provider_call(db, selected, mode)
        except InferenceUnavailable as exc:
            yield {
                "event": "error",
                "data": {"code": "usage_denied", "message": str(exc)[:300]},
            }
            return
        try:
            admission = await _admit_inference(selected, mode)
        except InferenceUnavailable as exc:
            yield {
                "event": "error",
                "data": {"code": "resource_refused", "message": str(exc)[:300]},
            }
            return
        admitted = True  # lease is held from here; release must always happen
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
            headers = {
                "Authorization": f"Bearer {call.credential or settings.litellm_master_key}"
            }
        else:
            url = f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"
            headers = {}

        try:
            # Start event is inside the protected region: if the SSE consumer
            # disconnects here, generator close still runs the finally and
            # releases the IRWM lease instead of leaking it.
            yield {
                "event": "start",
                "data": {
                    "model": selected,
                    "mode": mode,
                    "primary": status.primary,
                    "provider": call.provider,
                    "key_fingerprint": call.key_fingerprint,
                    "usage_decision": call.decision.as_dict() if call.decision else None,
                    "irwm": admission,
                },
            }
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
            if db is not None and mode == "hosted":
                from app.services.model_usage import ModelUsageService

                usage = await ModelUsageService(db).record(
                    model=selected,
                    provider=call.provider,
                    usage=None,
                    is_paid=call.is_paid,
                    decision=call.decision,
                    key_fingerprint=call.key_fingerprint,
                )
                yield {"event": "done", "data": {"finish_reason": "stop", "usage": usage}}
            else:
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
        finally:
            await _release_inference(selected, mode)


inference_service = InferenceService()
