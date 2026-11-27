"""Models.dev metadata client (specifications only, never availability)."""

from __future__ import annotations

from typing import Any, Dict

import httpx
import loguru

from app.core.config import settings
from app.services.providers.base import ModelSpec

logger = loguru.logger


def _model_type(model_id: str, modalities: Dict[str, Any]) -> str:
    lower = model_id.lower()
    if any(k in lower for k in ("embed", "rerank")):
        return "embedding"
    if any(k in lower for k in ("tts", "voice", "speech", "audio")):
        return "speech"
    if any(k in lower for k in ("image", "flux", "diffusion", "video")):
        return "image"
    if "vision" in lower or "image" in (modalities.get("input") or []):
        return "vision"
    return "llm"


class ModelsDevClient:
    async def fetch(self, provider: str) -> Dict[str, ModelSpec]:
        """Return normalised specifications, or {} when the catalogue is down."""
        try:
            async with httpx.AsyncClient(timeout=settings.models_dev_timeout_seconds) as client:
                response = await client.get(settings.models_dev_api_url)
            if response.status_code != 200:
                logger.warning(f"Models.dev returned {response.status_code}")
                return {}
            data = response.json()
        except Exception as exc:  # pragma: no cover - network/defensive
            logger.warning(f"Models.dev metadata unavailable: {exc}")
            return {}

        entry = data.get(provider) if isinstance(data, dict) else None
        raw_models = (entry or {}).get("models") or {}
        specs: Dict[str, ModelSpec] = {}
        for model_id, raw in raw_models.items():
            if not isinstance(raw, dict) or not model_id:
                continue
            modalities = raw.get("modalities") or {}
            limit = raw.get("limit") or {}
            cost = raw.get("cost") or {}
            try:
                context = int(limit.get("context") or 0) or None
            except (TypeError, ValueError):
                context = None
            is_free = (cost.get("input") in (0, 0.0, "0")) and (
                cost.get("output") in (0, 0.0, "0")
            )
            specs[model_id] = ModelSpec(
                provider=provider,
                model_id=model_id,
                display_name=str(raw.get("name") or model_id),
                model_type=_model_type(model_id, modalities),
                access_type="free" if is_free else "paid",
                endpoint_status="unknown",
                context_length=context,
                input_capabilities=list(modalities.get("input") or ["text"]),
                output_capabilities=list(modalities.get("output") or ["text"]),
                tool_calling=bool(raw.get("tool_call")),
                reasoning=bool(raw.get("reasoning")),
                structured_output=bool(raw.get("structured_output")),
                restrictions={"release_date": raw.get("release_date"), "open_weights": raw.get("open_weights")},
                metadata_source="models.dev",
            )
        return specs
