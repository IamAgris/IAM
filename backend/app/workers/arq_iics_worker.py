"""ARQ worker for governed IICS scheduled research (OD-08 runtime).

Uses the same Redis/ARQ runtime as the browser worker. A job is claimed once,
bounded retries are explicit, and failures are reported as failures.
"""

from __future__ import annotations

from typing import Any, Dict

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.iics.ledger import ActionLedger
from app.services.iics.scheduler import ScheduledResearchService
from app.services.research_service import ResearchService


async def run_scheduled_research(
    ctx: Dict[str, Any], *, task_id: str, actor: str = "iics"
) -> Dict[str, Any]:
    """Execute one governed recurring research job."""
    async with AsyncSessionLocal() as db:
        scheduler = ScheduledResearchService(db)
        task = await scheduler.get(task_id)
        if not task or task["status"] != "scheduled":
            return {"status": "skipped", "reason": "not_scheduled", "task_id": task_id}
        if not await scheduler.start(task_id):
            return {"status": "skipped", "reason": "already_claimed", "task_id": task_id}

        ledger = ActionLedger(db)
        await ledger.record(
            actor=actor,
            tool="scheduled_research",
            target=task["query"],
            idempotency_key=f"scheduled-research:{task_id}:{task['last_run_at']}",
            scope="public",
            permission_source="legal_gateway",
        )
        try:
            result = await ResearchService(db).research_topic(
                task["query"],
                store_as_memory=True,
                store_as_knowledge=False,
                max_results=10,
                governance_context={"iics_task_id": task_id, "autonomous": True},
            )
        except Exception as exc:  # bounded retry; no silent replay of side effects
            await scheduler.fail(task_id, f"{type(exc).__name__}: {exc}")
            raise
        await scheduler.complete(task_id)
        return {
            "status": "completed",
            "task_id": task_id,
            "sources": len(result.get("sources", []) or []),
        }


async def enqueue_due_research(ctx: Dict[str, Any]) -> int:
    """ARQ cron tick: enqueue due jobs through the existing Redis pool."""
    async with AsyncSessionLocal() as db:
        tasks = await ScheduledResearchService(db).due()
    redis = ctx.get("redis")
    if redis is None:
        return 0
    for task in tasks:
        await redis.enqueue_job("run_scheduled_research", task_id=task["task_id"])
    return len(tasks)


class WorkerSettings:
    functions = [run_scheduled_research, enqueue_due_research]
    cron_jobs = [cron(enqueue_due_research, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55})]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_timeout = 900
    max_jobs = 2
