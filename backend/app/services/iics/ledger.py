"""Cross-service external action ledger and global online-action budget.

IICS gap closure §2.3. Reuses the existing ARQ runtime; introduces no queue.
Idempotency keys prevent replay of already-verified external side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.iics import IICSAction


@dataclass(frozen=True)
class BudgetLimit:
    max_actions: int = 1000
    max_bytes: int = 100_000_000
    # None means no paid use is configured (free actions have cost 0). A signed
    # approval supplies a concrete ceiling when paid use is authorised.
    max_cost_units: Optional[int] = None


class BudgetGovernor:
    """Pure fail-closed budget check, shared by all online services."""

    @staticmethod
    def check(usage: Dict[str, int], limit: BudgetLimit) -> tuple[bool, str]:
        if usage.get("actions", 0) >= limit.max_actions:
            return False, "action_budget_exhausted"
        if usage.get("bytes", 0) >= limit.max_bytes:
            return False, "byte_budget_exhausted"
        if limit.max_cost_units is not None and usage.get("cost_units", 0) >= limit.max_cost_units:
            return False, "cost_budget_exhausted"
        return True, "within_budget"


class ActionLedger:
    """Append-only action records with verification and budget accounting."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _row_dict(row: IICSAction) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "actor": row.actor,
            "tool": row.tool,
            "target": row.target,
            "scope": row.scope,
            "permission_source": row.permission_source,
            "approval_ref": row.approval_ref,
            "idempotency_key": row.idempotency_key,
            "status": row.status,
            "verification_result": dict(row.verification_result or {}),
            "bytes_transferred": int(row.bytes_transferred or 0),
            "cost_units": int(row.cost_units or 0),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    async def record(
        self,
        *,
        actor: str,
        tool: str,
        target: str,
        idempotency_key: str,
        scope: str = "public",
        permission_source: str = "legal_gateway",
        approval_ref: Optional[str] = None,
        bytes_transferred: int = 0,
        cost_units: int = 0,
        status: str = "planned",
    ) -> Dict[str, Any]:
        """Record an action once. Reusing a key returns the existing record."""
        result = await self.db.execute(
            select(IICSAction).where(IICSAction.idempotency_key == idempotency_key)
        )
        existing = result.scalar_one_or_none()
        if existing:
            payload = self._row_dict(existing)
            payload["duplicate"] = True
            return payload
        row = IICSAction(
            actor=actor,
            tool=tool,
            target=target,
            scope=scope,
            permission_source=permission_source,
            approval_ref=approval_ref,
            idempotency_key=idempotency_key,
            status=status,
            bytes_transferred=bytes_transferred,
            cost_units=cost_units,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        payload = self._row_dict(row)
        payload["duplicate"] = False
        return payload

    async def mark(
        self,
        idempotency_key: str,
        status: str,
        verification_result: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(IICSAction).where(IICSAction.idempotency_key == idempotency_key)
        )
        row: Any = result.scalar_one_or_none()
        if not row:
            return None
        row.status = status
        if verification_result is not None:
            row.verification_result = verification_result
        await self.db.commit()
        await self.db.refresh(row)
        return self._row_dict(row)

    async def usage(self, window: timedelta = timedelta(hours=1)) -> Dict[str, int]:
        """Aggregate current-window usage across all services."""
        since = datetime.now(timezone.utc) - window
        result = await self.db.execute(
            select(
                func.count(IICSAction.id),
                func.coalesce(func.sum(IICSAction.bytes_transferred), 0),
                func.coalesce(func.sum(IICSAction.cost_units), 0),
            ).where(IICSAction.created_at >= since)
        )
        actions, bytes_, cost = result.one()
        return {
            "actions": int(actions or 0),
            "bytes": int(bytes_ or 0),
            "cost_units": int(cost or 0),
        }

    async def check_budget(self, limit: BudgetLimit) -> tuple[bool, str]:
        return BudgetGovernor.check(await self.usage(), limit)

    async def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(IICSAction).order_by(IICSAction.created_at.desc()).limit(limit)
        )
        return [self._row_dict(row) for row in result.scalars().all()]
