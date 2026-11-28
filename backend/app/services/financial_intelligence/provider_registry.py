"""§18 provider registry — gates recorded before any adapter is enabled."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.financial_intelligence import ProviderRegistryEntry
from app.models.security import AuditEvent
from app.services.financial_intelligence.policy import (
    IntelligenceDenied,
    PROVIDER_CATEGORIES,
    PROVIDER_GATES,
    provider_eligibility,
    require_eligible_provider,
)
from app.services.financial_intelligence.provider_catalogue import PROVIDER_CANDIDATES


class ProviderRegistryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.financial_provider_registry_enabled,
            "categories": list(PROVIDER_CATEGORIES),
            "gates": list(PROVIDER_GATES),
            "credentials_are_env_var_names": True,
            "no_credentials_stored": True,
        }

    async def register(
        self,
        *,
        name: str,
        category: str,
        access_model: str,
        documented_api_and_auth: bool = False,
        commercial_use: bool = False,
        automated_use: bool = False,
        south_africa_supported: bool = False,
        sandbox_available: bool = False,
        licence_required: bool = False,
        licence_requirements_recorded: bool = False,
        gates_reviewed: bool = False,
        notes: Optional[str] = None,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        if not settings.financial_provider_registry_enabled:
            raise IntelligenceDenied("provider registry is disabled")
        if not name or category not in PROVIDER_CATEGORIES:
            raise IntelligenceDenied("name and a known provider category are required")
        if access_model not in ("free", "paid", "mixed"):
            raise IntelligenceDenied("access_model must be free, paid or mixed")

        result = await self.db.execute(select(ProviderRegistryEntry))
        existing = next((row for row in result.scalars().all() if row.name == name), None)
        if existing:
            raise IntelligenceDenied("provider already registered")

        entry = ProviderRegistryEntry(
            name=name,
            category=category,
            access_model=access_model,
            documented_api_and_auth=bool(documented_api_and_auth),
            commercial_use=bool(commercial_use),
            automated_use=bool(automated_use),
            south_africa_supported=bool(south_africa_supported),
            sandbox_available=bool(sandbox_available),
            licence_required=bool(licence_required),
            licence_requirements_recorded=bool(licence_requirements_recorded),
            gates_reviewed=bool(gates_reviewed),
            notes=notes,
            adapter_enabled=False,
        )
        self.db.add(entry)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="financial_provider_registered",
                actor=actor,
                target=str(entry.id),
                details={
                    "name": name,
                    "category": category,
                    "access_model": access_model,
                    "adapter_enabled": False,
                },
            )
        )
        await self.db.commit()
        return self._entry(entry)

    async def seed_candidates(self, actor: str = "iam") -> Dict[str, Any]:
        """Record the §18 candidate providers once, with all gates unreviewed.

        This is local research data only: no network call, no credential, no
        adapter enablement and no real-money authority is created. Re-running is
        idempotent — existing entries are never overwritten.
        """
        result = await self.db.execute(select(ProviderRegistryEntry))
        existing_names = {row.name for row in result.scalars().all()}
        created = 0
        for candidate in PROVIDER_CANDIDATES:
            if candidate.name in existing_names:
                continue
            entry = ProviderRegistryEntry(
                name=candidate.name,
                category=candidate.category,
                access_model="mixed",
                documented_api_and_auth=False,
                commercial_use=False,
                automated_use=False,
                south_africa_supported=False,
                sandbox_available=False,
                licence_required=False,
                licence_requirements_recorded=False,
                gates_reviewed=False,
                notes=candidate.note,
                adapter_enabled=False,
            )
            self.db.add(entry)
            created += 1
        if created:
            self.db.add(
                AuditEvent(
                    event_type="financial_provider_catalogue_seeded",
                    actor=actor,
                    target="provider_catalogue",
                    details={
                        "created": created,
                        "candidates": len(PROVIDER_CANDIDATES),
                        "all_adapters_disabled": True,
                    },
                )
            )
            await self.db.commit()
        return {
            "created": created,
            "existing": len(PROVIDER_CANDIDATES) - created,
            "candidates": len(PROVIDER_CANDIDATES),
            "all_adapters_disabled": True,
        }

    async def entries(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(ProviderRegistryEntry))
        return [self._entry(row) for row in result.scalars().all()]

    async def evaluate(self, name: str) -> Dict[str, Any]:
        entry = await self._entry_by_name(name)
        return {"provider": name, **provider_eligibility(entry)}

    async def enable_adapter(self, name: str, actor: str = "iam") -> Dict[str, Any]:
        """Enable an adapter only when every §18 gate is satisfied.

        Enabling an adapter still does not open a trading, wagering or payment
        path — those remain governed by their own signed approval controls.
        """
        if not settings.financial_provider_registry_enabled:
            raise IntelligenceDenied("provider registry is disabled")
        entry = await self._entry_by_name(name)
        require_eligible_provider(entry)
        entry.adapter_enabled = True  # type: ignore[assignment]
        entry.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        self.db.add(
            AuditEvent(
                event_type="financial_provider_adapter_enabled",
                actor=actor,
                target=str(entry.id),
                details={"name": name, "gates": provider_eligibility(entry)["gates"]},
            )
        )
        await self.db.commit()
        return self._entry(entry)

    async def _entry_by_name(self, name: str) -> ProviderRegistryEntry:
        result = await self.db.execute(select(ProviderRegistryEntry))
        entry = next((row for row in result.scalars().all() if row.name == name), None)
        if not entry:
            raise LookupError("provider not registered")
        return entry

    @staticmethod
    def _entry(entry: ProviderRegistryEntry) -> Dict[str, Any]:
        return {
            "id": str(entry.id),
            "name": entry.name,
            "category": entry.category,
            "access_model": entry.access_model,
            "documented_api_and_auth": bool(entry.documented_api_and_auth),
            "commercial_use": bool(entry.commercial_use),
            "automated_use": bool(entry.automated_use),
            "south_africa_supported": bool(entry.south_africa_supported),
            "sandbox_available": bool(entry.sandbox_available),
            "licence_required": bool(entry.licence_required),
            "licence_requirements_recorded": bool(entry.licence_requirements_recorded),
            "gates_reviewed": bool(entry.gates_reviewed),
            "notes": entry.notes,
            "adapter_enabled": bool(entry.adapter_enabled),
            **provider_eligibility(entry),
        }
