"""Bounded autonomous live-research monitoring (proposed Doc 34 extension).

Recurring public-web research only. No authority to spend, disclose private
data, enter agreements or crawl without limits. Uses the shared engine and the
existing ARQ runtime for execution; this module owns scheduling state only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.live_evidence import LiveResearchTask

MAX_TASKS = 50
MIN_INTERVAL_MINUTES = 15
MAX_INTERVAL_MINUTES = 10080


def validate_task(topic: str, query: str, interval_minutes: int) -> None:
    if not topic.strip() or not query.strip():
        raise ValueError("topic and query are required")
    if not MIN_INTERVAL_MINUTES <= interval_minutes <= MAX_INTERVAL_MINUTES:
        raise ValueError("interval_minutes must be between 15 and 10080")


class LiveResearchMonitor:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self, topic: str, query: str, interval_minutes: int = 60, owner: str = "creator"
    ) -> Dict[str, Any]:
        validate_task(topic, query, interval_minutes)
        count = (await self.db.execute(select(func.count(LiveResearchTask.id)))).scalar_one()
        if int(count) >= MAX_TASKS:
            raise PermissionError(f"maximum {MAX_TASKS} monitored topics reached")
        task = LiveResearchTask(
            topic=topic.strip()[:200],
            query=query.strip()[:1000],
            interval_minutes=interval_minutes,
            owner=owner,
            next_run_at=datetime.now(timezone.utc),
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return self._row(task)

    async def list(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(LiveResearchTask))
        return [self._row(row) for row in result.scalars().all()]

    async def enable(self, task_id: str, enabled: bool) -> bool:
        task = await self.db.get(LiveResearchTask, task_id)
        if not task:
            return False
        task = cast(Any, task)
        task.enabled = bool(enabled)
        await self.db.commit()
        return True

    async def remove(self, task_id: str) -> bool:
        task = await self.db.get(LiveResearchTask, task_id)
        if not task:
            return False
        await self.db.delete(task)
        await self.db.commit()
        return True

    async def run_due(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Run at most ``limit`` due tasks through the shared engine."""
        from app.services.live_information_policy import SearchTriggerClassifier, collect_live_evidence

        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(LiveResearchTask)
            .where(LiveResearchTask.enabled.is_(True))
            .where(LiveResearchTask.next_run_at <= now)
            .limit(min(max(limit, 1), 5))
        )
        tasks = result.scalars().all()
        summaries: List[Dict[str, Any]] = []
        for task in tasks:
            task = cast(Any, task)
            trigger = SearchTriggerClassifier().classify(task.query)
            evidence = await collect_live_evidence(
                task.query, trigger=trigger, db=self.db
            )
            task.last_run_at = now
            task.next_run_at = now + timedelta(minutes=task.interval_minutes)
            summaries.append(
                {
                    "topic": task.topic,
                    "query": task.query,
                    "provider": evidence.provider,
                    "result_count": len(evidence.results),
                    "errors": evidence.errors,
                }
            )
        if tasks:
            await self.db.commit()
        return summaries

    @staticmethod
    def _row(row: LiveResearchTask) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "topic": row.topic,
            "query": row.query,
            "interval_minutes": row.interval_minutes,
            "enabled": bool(row.enabled),
            "owner": row.owner,
            "last_run_at": row.last_run_at.isoformat() if row.last_run_at else None,
            "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        }
