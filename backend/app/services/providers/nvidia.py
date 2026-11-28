"""NVIDIA provider — one credential, live catalogue, external metadata."""

from __future__ import annotations

from typing import Any, Dict, List

import httpx
import loguru

from app.core.config import settings
from app.services.providers.base import BaseProvider, ModelSpec
from app.services.providers.models_dev import ModelsDevClient

logger = loguru.logger

_FREE_HINTS = (
    "llama", "qwen", "deepseek", "nemotron", "mistral", "gemma", "phi",
    "embedding", "gpt-oss", "glm", "kimi", "minimax", "step", "solar",
)


def _model_type(model_id: str) -> str:
    lower = model_id.lower()
    if any(k in lower for k in ("embed", "rerank")):
        return "embedding"
    if any(k in lower for k in ("tts", "voice", "speech", "audio", "whisper")):
        return "speech"
    if any(k in lower for k in ("image", "flux", "diffusion", "video", "transfer")):
        return "image"
    if any(k in lower for k in ("vision", "vl", "vlm", "paligemma", "bevformer")):
        return "vision"
    return "llm"


def _is_free_hint(model_id: str) -> bool:
    """Catalogue-side hint only; the availability monitor is authoritative."""
    return any(hint in model_id.lower() for hint in _FREE_HINTS)


class NvidiaProvider(BaseProvider):
    name = "nvidia"

    async def discover(self) -> List[ModelSpec]:
        if not settings.nvidia_api_key:
            return []
        specs: List[ModelSpec] = []
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(
                    f"{settings.nvidia_base_url.rstrip('/')}/models",
                    headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
                )
            if response.status_code != 200:
                logger.warning(f"NVIDIA catalogue returned {response.status_code}")
                return []
            data = response.json()
        except Exception as exc:  # pragma: no cover - network/defensive
            logger.warning(f"NVIDIA discovery failed: {exc}")
            return []

        for entry in data.get("data", []) if isinstance(data, dict) else []:
            model_id = str(entry.get("id") or "").strip()
            if not model_id:
                continue
            free = _is_free_hint(model_id)
            if settings.nvidia_free_only and not free:
                continue
            specs.append(
                ModelSpec(
                    provider=self.name,
                    model_id=model_id,
                    display_name=str(entry.get("id") or model_id),
                    model_type=_model_type(model_id),
                    access_type="free" if free else "paid",
                    endpoint_status="unknown",
                    restrictions={"source": "nvidia_catalog", "account_access": "unverified"},
                    metadata_source="nvidia_catalog",
                )
            )
        return specs

    async def metadata(self) -> Dict[str, ModelSpec]:
        return await ModelsDevClient().fetch(self.name)
