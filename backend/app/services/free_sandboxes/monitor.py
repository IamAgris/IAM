"""Background quota/expiry monitoring for free providers (Doc 22 §3.8/§3.12)."""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.freesandbox import FreeSandboxProvider, FreeSandboxQuotaSnapshot
from app.services.free_sandboxes.base import SandboxError
from app.services.free_sandboxes.service import FreeSandboxService


class FreeSandboxMonitor:
    """Polls provider quotas and refreshes the expiry calendar."""

    def __init__(self, service: FreeSandboxService):
        self.service = service

    async def poll(self) -> List[Dict[str, Any]]:
        manager = self.service.manager
        manager.require_enabled()
        found = await self.service.db.execute(
            select(FreeSandboxProvider).where(FreeSandboxProvider.is_active.is_(True))
        )
        outcomes = []
        for record in found.scalars().all():
            try:
                outcome = await self.service.verify_quota(record.name)
            except SandboxError as exc:
                outcome = {
                    "provider": record.name,
                    "allowed": False,
                    "reason": str(exc),
                }
            outcome["health"] = manager.health().get(record.name)
            outcomes.append(outcome)
        return outcomes

    async def expiry_calendar(self) -> List[Dict[str, Any]]:
        result = await self.service.db.execute(select(FreeSandboxQuotaSnapshot))
        return [
            {
                "provider_id": str(s.provider_id),
                "resets_at": s.resets_at.isoformat() if s.resets_at else None,
                "used_percent": float(s.used_percent) if s.used_percent is not None else None,
            }
            for s in result.scalars().all()
            if s.resets_at is not None
        ]
