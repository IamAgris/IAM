"""ARQ worker for governed IICS scheduled research (OD-08 runtime).

Uses the same Redis/ARQ runtime as the browser worker. A job is claimed once,
bounded retries are explicit, and failures are reported as failures.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.iics.egress import default_gateway, enforce
from app.services.iics.ledger import ActionLedger
from app.services.iics.scheduler import ScheduledResearchService
from app.services.iics.site_policy import SitePolicyStore
from app.services.iics.source_registry import SourceRegistry
from app.services.iics.threat_intel import AdvisoryIngestor
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
            result = await ResearchService().research_topic(  # type: ignore[no-untyped-call]
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


async def poll_threat_feeds(ctx: Dict[str, Any]) -> int:
    """Poll allowlisted advisory feeds through the egress gateway."""
    ingested = 0
    async with AsyncSessionLocal() as db:
        ingestor = AdvisoryIngestor(db)
        feeds = [item.strip() for item in settings.iics_threat_feeds.split(",") if item.strip()]
        for url in feeds:
            if not enforce(url).allowed:
                continue
            result = await default_gateway().fetch(url)
            if not result.get("ok"):
                continue
            try:
                payload = json.loads(result.get("body") or "{}")
            except ValueError:
                continue
            if not isinstance(payload, dict):
                continue
            source = "nvd" if "nvd" in url.lower() else "osv"
            outcome = await ingestor.ingest(payload, source)
            ingested += int(outcome.get("inserted") or 0)
    return ingested


async def refresh_site_policies(ctx: Dict[str, Any]) -> int:
    """Refresh robots/TOS snapshots for registered web sources."""
    refreshed = 0
    async with AsyncSessionLocal() as db:
        store = SitePolicyStore(db)
        for source in await SourceRegistry(db).list(active_only=True):
            url = str(source.get("url") or "")
            if not url or not url.lower().startswith(("http://", "https://")):
                continue
            from urllib.parse import urljoin

            robots_url = urljoin(url, "/robots.txt")
            if not enforce(robots_url).allowed:
                continue
            result = await default_gateway().fetch(robots_url)
            if not result.get("ok"):
                continue
            await store.record(
                str(source.get("domain") or ""),
                robots_text=str(result.get("body") or "")[:100_000],
                ttl_hours=settings.iics_site_policy_refresh_minutes // 60 or 1,
                source_url=robots_url,
                notes="robots.txt is a crawling signal, never permission",
            )
            refreshed += 1
    return refreshed


def _threat_feed_minutes() -> set[int]:
    """Translate the configured interval into cron minutes (bounded 1–60)."""
    step = max(1, min(60, int(settings.iics_threat_feed_interval_minutes)))
    return set(range(0, 60, step))


class WorkerSettings:
    functions = [run_scheduled_research, enqueue_due_research]
    cron_jobs = [
        cron(enqueue_due_research, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
        cron(poll_threat_feeds, minute=_threat_feed_minutes()),
        cron(refresh_site_policies, minute={0, 30}),
    ]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    job_timeout = 900
    max_jobs = 2
