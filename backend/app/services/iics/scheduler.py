"""Scheduled research executor on the existing OD-08 ARQ runtime (§2.3).

No new queue, no new cron service. Jobs are governed records with deadlines,
bounded retries and no replay of already-verified side effects.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.iics import IICSScheduledTask
from app.services.iics.source_registry import FRESHNESS_TTL_HOURS

ACTIVE_STATUSES = frozenset({"scheduled", "running"})


class ScheduledResearchError(PermissionError):
    """Raised when a scheduled job is outside its governed lifecycle."""


class ScheduledResearchService:
    """Create, discover and advance recurring research jobs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _row_dict(row: IICSScheduledTask) -> Dict[str, Any]:
        return {
            "task_id": row.task_id,
            "goal": row.goal,
            "query": row.query,
            "freshness_class": row.freshness_class,
            "cadence_minutes": int(row.cadence_minutes),
            "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
            "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
            "status": row.status,
            "attempts": int(row.attempts or 0),
            "last_error": row.last_error,
        }

    async def create(
        self,
        goal: str,
        query: str,
        *,
        cadence_minutes: int = 1440,
        freshness_class: str = "documentation",
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if cadence_minutes < 5:
            raise ScheduledResearchError("cadence_minutes must be at least 5")
        if freshness_class not in FRESHNESS_TTL_HOURS:
            raise ScheduledResearchError("unknown freshness_class")
        identifier = task_id or f"iicsr_{secrets.token_hex(12)}"
        existing = await self.get(identifier)
        if existing:
            payload = dict(existing)
            payload["duplicate"] = True
            return payload
        now = datetime.now(timezone.utc)
        row = IICSScheduledTask(
            task_id=identifier,
            goal=goal,
            query=query,
            freshness_class=freshness_class,
            cadence_minutes=cadence_minutes,
            next_run_at=now + timedelta(minutes=cadence_minutes),
            status="scheduled",
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        payload = self._row_dict(row)
        payload["duplicate"] = False
        return payload

    async def get(self, task_id: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(IICSScheduledTask).where(IICSScheduledTask.task_id == task_id)
        )
        row = result.scalar_one_or_none()
        return self._row_dict(row) if row else None

    async def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(IICSScheduledTask).order_by(IICSScheduledTask.next_run_at).limit(limit)
        )
        return [self._row_dict(row) for row in result.scalars().all()]

    async def due(self, limit: int = 10) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(IICSScheduledTask)
            .where(IICSScheduledTask.status == "scheduled")
            .where(IICSScheduledTask.next_run_at <= now)
            .order_by(IICSScheduledTask.next_run_at)
            .limit(limit)
        )
        return [self._row_dict(row) for row in result.scalars().all()]

    async def start(self, task_id: str) -> bool:
        """Claim a job once; a second worker must not replay it."""
        from sqlalchemy import update

        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            update(IICSScheduledTask)
            .where(IICSScheduledTask.task_id == task_id)
            .where(IICSScheduledTask.status == "scheduled")
            .where(IICSScheduledTask.next_run_at <= now)
            .values(status="running", last_run_at=now, last_error=None)
        )
        await self.db.commit()
        return bool(int(getattr(result, "rowcount", 0) or 0))

    async def complete(self, task_id: str) -> bool:
        from sqlalchemy import update

        row = await self.get(task_id)
        if not row or row["status"] != "running":
            return False
        cadence = int(row["cadence_minutes"])
        next_run = datetime.now(timezone.utc) + timedelta(minutes=cadence)
        result = await self.db.execute(
            update(IICSScheduledTask)
            .where(IICSScheduledTask.task_id == task_id)
            .where(IICSScheduledTask.status == "running")
            .values(status="scheduled", next_run_at=next_run, attempts=0)
        )
        await self.db.commit()
        return bool(int(getattr(result, "rowcount", 0) or 0))

    async def fail(self, task_id: str, error: str, max_attempts: int = 3) -> bool:
        from sqlalchemy import update

        row = await self.get(task_id)
        if not row or row["status"] != "running":
            return False
        attempts = int(row["attempts"]) + 1
        status = "failed" if attempts >= max_attempts else "scheduled"
        backoff = min(60 * attempts, 3600)
        values: Dict[str, Any] = {
            "attempts": attempts,
            "last_error": error[:1000],
            "status": status,
        }
        if status == "scheduled":
            values["next_run_at"] = datetime.now(timezone.utc) + timedelta(minutes=backoff)
        result = await self.db.execute(
            update(IICSScheduledTask)
            .where(IICSScheduledTask.task_id == task_id)
            .where(IICSScheduledTask.status == "running")
            .values(**values)
        )
        await self.db.commit()
        return bool(int(getattr(result, "rowcount", 0) or 0))

    async def set_status(self, task_id: str, status: str) -> bool:
        if status not in ACTIVE_STATUSES | {"paused", "cancelled", "completed"}:
            raise ScheduledResearchError("unknown status")
        from sqlalchemy import update

        result = await self.db.execute(
            update(IICSScheduledTask)
            .where(IICSScheduledTask.task_id == task_id)
            .values(status=status)
        )
        await self.db.commit()
        return bool(int(getattr(result, "rowcount", 0) or 0))
