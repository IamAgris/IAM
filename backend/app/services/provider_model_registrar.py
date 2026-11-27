"""Runtime LiteLLM registration for discovered free models (OD-52 Phase C).

IAM keeps the credential in LiteLLM's environment; the registration payload
contains only the env-variable reference, never a secret. Models registered
here are marked ``iam_managed`` so static config models are never deleted.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

import httpx
import loguru

from app.core.config import settings
from app.services.providers.base import ModelSpec

logger = loguru.logger

# Catalogue entries that exist but cannot serve text chat completions with a
# free-tier key (embeddings, safety classifiers, multimodal/omni models...).
_INELIGIBLE = re.compile(
    r"omni|embed|rerank|safety|guard|moderation|asr|tts|speech|voice|whisper|"
    r"speaker|audio|sound|vision|image|depth|segment|detection|bevformer|"
    r"streampetr|sparsedrive|ocr|video|diffusion|flux",
    re.IGNORECASE,
)


class ProviderModelRegistrar:
    def __init__(self) -> None:
        self.base = settings.litellm_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.litellm_master_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, path: str, payload: Dict[str, Any] | None = None
    ) -> Tuple[int, Any]:
        url = f"{self.base}{path}"
        try:
            async with httpx.AsyncClient(
                timeout=settings.litellm_model_management_timeout_seconds
            ) as client:
                response = await client.request(
                    method, url, headers=self.headers, json=payload
                )
            return response.status_code, response.json() if response.content else {}
        except Exception as exc:  # pragma: no cover - network/defensive
            logger.warning(f"LiteLLM model management failed ({path}): {exc}")
            return 0, {"error": str(exc)[:200]}

    @staticmethod
    def _managed(entry: Dict[str, Any]) -> bool:
        info = entry.get("model_info") or {}
        return bool(info.get("iam_managed")) or bool(
            (info.get("metadata") or {}).get("iam_managed")
        )

    @staticmethod
    def _entry_id(entry: Dict[str, Any]) -> Any:
        """DB-backed /model/info entries carry the id inside model_info."""
        info = entry.get("model_info") or {}
        return entry.get("id") or entry.get("model_id") or info.get("id")

    @staticmethod
    def _entries(data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if isinstance(data, dict):
            for key in ("data", "models"):
                value = data.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    async def _list(self) -> List[Dict[str, Any]]:
        status, data = await self._request("GET", "/model/info")
        return self._entries(data) if status == 200 else []

    @classmethod
    def _eligible(cls, spec: ModelSpec) -> bool:
        return (
            spec.model_type == "llm"
            and spec.api_protocol == "chat_completions"
            and not _INELIGIBLE.search(spec.model_id)
        )

    async def _chat_smoke(self, alias: str) -> tuple[bool, str]:
        """Prove the alias actually answers a text chat request before exposing it."""
        status, data = await self._request(
            "POST",
            "/chat/completions",
            {
                "model": alias,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            },
        )
        if 200 <= status < 300:
            return True, ""
        detail = ""
        if isinstance(data, dict):
            detail = str((data.get("error") or {}).get("message") or "")[:200]
        return False, detail or f"status {status}"

    async def _delete_by_name(self, name: str) -> bool:
        entries = await self._list()
        for entry in entries:
            if str(entry.get("model_name") or "") != name:
                continue
            identifier = self._entry_id(entry)
            if not identifier:
                return False
            status, _ = await self._request("POST", "/model/delete", {"id": identifier})
            return 200 <= status < 300
        return False

    async def sync(self, specs: List[ModelSpec]) -> Dict[str, Any]:
        """Create missing free models and retire IAM-managed entries no longer listed."""
        if not settings.model_catalog_registration_enabled:
            return {
                "enabled": False,
                "reason": "OD-52 not confirmed; runtime registration is disabled",
            }
        existing = await self._list()
        by_name = {
            str(entry.get("model_name") or ""): entry
            for entry in existing
            if entry.get("model_name")
        }
        wanted = {
            spec.alias: spec
            for spec in specs
            if spec.alias and spec.access_type == "free" and self._eligible(spec)
        }
        created: List[str] = []
        skipped: List[str] = []
        retired: List[str] = []
        errors: List[Dict[str, str]] = []
        blocked: set[str] = set()
        for alias, spec in wanted.items():
            if alias in by_name:
                ok, detail = await self._chat_smoke(alias)
                if ok:
                    skipped.append(alias)
                else:
                    if await self._delete_by_name(alias):
                        retired.append(alias)
                    blocked.add(alias)
                    errors.append({"alias": alias, "error": f"chat smoke failed: {detail}"})
                continue
            if alias in blocked:
                continue
            payload = {
                "model_name": alias,
                "litellm_params": {
                    "model": f"openai/{spec.model_id}",
                    "api_key": "os.environ/NVIDIA_API_KEY",
                    "api_base": settings.nvidia_base_url,
                },
                "model_info": {
                    "iam_managed": True,
                    "provider": spec.provider,
                    "access_type": "free",
                    "metadata_source": spec.metadata_source,
                },
            }
            status, data = await self._request("POST", "/model/new", payload)
            if not (200 <= status < 300):
                errors.append({"alias": alias, "error": str(data)[:200]})
                continue
            ok, detail = await self._chat_smoke(alias)
            if ok:
                created.append(alias)
            else:
                await self._delete_by_name(alias)
                blocked.add(alias)
                errors.append({"alias": alias, "error": f"chat smoke failed: {detail}"})
        for name, entry in by_name.items():
            if self._managed(entry) and name not in wanted:
                identifier = self._entry_id(entry)
                if not identifier:
                    continue
                status, _ = await self._request(
                    "POST", "/model/delete", {"id": identifier}
                )
                if 200 <= status < 300:
                    retired.append(name)
        return {
            "enabled": True,
            "created": created,
            "skipped": skipped,
            "retired": retired,
            "errors": errors,
            "claim": "registered aliases passed a text-chat smoke; ongoing availability still monitored",
        }
