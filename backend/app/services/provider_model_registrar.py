"""Runtime LiteLLM registration for discovered free models (OD-52 Phase C).

IAM keeps the credential in LiteLLM's environment; the registration payload
contains only the env-variable reference, never a secret. Models registered
here are marked ``iam_managed`` so static config models are never deleted.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import httpx
import loguru

from app.core.config import settings
from app.services.providers.base import ModelSpec

logger = loguru.logger


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
            if spec.alias and spec.access_type == "free"
        }
        created: List[str] = []
        skipped: List[str] = []
        errors: List[Dict[str, str]] = []
        for alias, spec in wanted.items():
            if alias in by_name:
                skipped.append(alias)
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
            if 200 <= status < 300:
                created.append(alias)
            else:
                errors.append({"alias": alias, "error": str(data)[:200]})
        retired: List[str] = []
        for name, entry in by_name.items():
            if self._managed(entry) and name not in wanted:
                identifier = entry.get("id") or entry.get("model_id")
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
            "claim": "registered aliases are executable; availability still unverified",
        }
