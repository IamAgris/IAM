"""Dual-source model discovery and registry maintenance (OD-52 Phase B).

NVIDIA's catalogue supplies current ids; Models.dev supplies specifications.
Neither proves that a free endpoint works — endpoint_status stays 'unknown'
until the Phase D availability monitor tests it.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.modelrouter import AIProvider, DiscoveredModel
from app.services.provider_model_registrar import ProviderModelRegistrar
from app.services.providers.base import BaseProvider, ModelSpec

_PROVIDERS: Dict[str, str] = {"nvidia": "app.services.providers.nvidia.NvidiaProvider"}


def _provider(name: str) -> Optional[BaseProvider]:
    path = _PROVIDERS.get(name)
    if not path:
        return None
    module_name, class_name = path.rsplit(".", 1)
    module = __import__(module_name, fromlist=[class_name])
    from typing import cast

    return cast(BaseProvider, getattr(module, class_name)())


def _alias(model_id: str) -> str:
    return "nv-" + re.sub(r"[^a-zA-Z0-9]+", "-", model_id).strip("-")[:90]


class ModelDiscoveryService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.registration: Optional[Dict[str, Any]] = None

    @staticmethod
    def merge(
        catalog: List[ModelSpec], metadata: Dict[str, ModelSpec], provider: str
    ) -> List[ModelSpec]:
        """Live catalogue wins for access; metadata wins for specifications."""
        merged: Dict[str, ModelSpec] = dict(metadata)
        for live in catalog:
            existing = merged.get(live.model_id)
            if existing is None:
                merged[live.model_id] = live
                continue
            existing.access_type = live.access_type
            existing.restrictions = {**existing.restrictions, **live.restrictions}
            existing.metadata_source = f"{live.metadata_source}+{existing.metadata_source}"
        result = list(merged.values())
        if settings.nvidia_free_only and provider == "nvidia":
            result = [spec for spec in result if spec.access_type == "free"]
        # A catalogue entry is never proof of an available endpoint.
        for spec in result:
            spec.endpoint_status = "unknown"
            if spec.access_type == "free":
                spec.alias = _alias(spec.model_id)
        return result

    async def discover(self, provider_name: str = "nvidia") -> List[Dict[str, Any]]:
        provider = _provider(provider_name)
        if provider is None:
            return []
        catalog = await provider.discover()
        metadata = await provider.metadata()
        specs = self.merge(catalog, metadata, provider_name)
        if not specs:
            return []
        written = await self._persist(provider_name, specs)
        # Phase C: make eligible free models executable through LiteLLM.
        # The registrar is a no-op until OD-52 enables it.
        self.registration = await ProviderModelRegistrar().sync(specs)
        return written

    async def _persist(self, provider_name: str, specs: List[ModelSpec]) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(AIProvider).where(AIProvider.name == provider_name)
        )
        provider_row = result.scalar_one_or_none()
        if not provider_row:
            return []

        existing_result = await self.db.execute(
            select(DiscoveredModel).where(DiscoveredModel.provider_id == provider_row.id)
        )
        existing = {
            str(row.model_id): cast(Any, row) for row in existing_result.scalars().all()
        }
        snapshot = {
            "model_ids": [
                row.model_id
                for row in existing.values()
                if row.endpoint_status == "available"
            ],
            "at": datetime.now(timezone.utc).isoformat(),
        }
        written: List[Dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        for spec in specs:
            row = existing.get(spec.model_id)
            if row is None:
                row = DiscoveredModel(
                    provider_id=provider_row.id,
                    model_id=spec.model_id,
                    display_name=spec.display_name,
                )
                self.db.add(row)
            row.display_name = spec.display_name
            row.model_type = spec.model_type
            row.access_type = spec.access_type
            row.endpoint_status = spec.endpoint_status
            row.alias = spec.alias if spec.access_type == "free" else None
            row.context_length = spec.context_length
            row.input_capabilities = spec.input_capabilities
            row.output_capabilities = spec.output_capabilities
            row.tool_calling = spec.tool_calling
            row.reasoning = spec.reasoning
            row.structured_output = spec.structured_output
            row.api_protocol = spec.api_protocol
            row.restrictions = spec.restrictions
            row.metadata_source = spec.metadata_source
            row.last_checked_at = now
            row.last_known_good = snapshot
            row.is_free = spec.access_type == "free"
            written.append(spec.as_dict())
        await self.db.flush()
        await self.db.commit()
        return written
