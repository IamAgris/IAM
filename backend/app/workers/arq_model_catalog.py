"""OD-52 scheduled model-catalogue refresh on the existing OD-08 ARQ runtime.

    docker compose --profile catalog-arq up -d

Discovery, metadata refresh and availability checks are no-ops unless their
OD-52 flags are enabled, so this worker is safe to deploy before confirmation.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

import loguru
from arq import cron

from app.core.config import settings
from app.core.database import get_session_factory
from app.services.endpoint_availability import EndpointAvailabilityMonitor
from app.services.intel_router_service import IntelligenceRouter
from app.services.model_discovery import ModelDiscoveryService

logger = loguru.logger


async def refresh_catalog(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Discover, register and re-test free NVIDIA models."""
    async with get_session_factory()() as db:
        await IntelligenceRouter(db).initialize_providers()  # type: ignore[no-untyped-call]
        service = ModelDiscoveryService(db)
        models = await service.discover("nvidia")
        availability = await EndpointAvailabilityMonitor(db).monitor_all()
    outcome = {
        "discovered": len(models),
        "registration": service.registration,
        "availability_checked": len(availability),
    }
    logger.info(f"model catalogue refresh: {outcome}")
    return outcome


async def run_post_deploy_checks(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Hourly regression monitoring for deployed models (OD-40 safeguard 9).

    A no-op unless an operator enables ``post_deploy_monitor_enabled``. A
    regression only triggers rollback when the separate auto-rollback flag is
    on *and* the signed release gate authorises the previous version.
    """
    if not settings.post_deploy_monitor_enabled:
        return {"enabled": False, "checked": 0}

    from app.services.ai_research.lm_eval import default_lm_eval_driver
    from app.services.ai_research.post_deploy import check_regression
    from app.services.ai_research.release_gate import (
        ModelReleaseService,
        default_release_store,
    )

    evaluator = default_lm_eval_driver()
    if evaluator is None:
        return {"enabled": True, "checked": 0, "reason": "no trusted evaluator configured"}

    checked = []
    async with get_session_factory()() as db:
        store = default_release_store()  # type: ignore[no-untyped-call]
        service = ModelReleaseService(db, store)
        for version in service.registry.deployed_versions():
            result = await check_regression(
                db,
                version.model,
                version.version,
                evaluate=lambda model: asyncio.to_thread(evaluator.evaluate, None, model),
                store=store,
                actor="post-deploy-monitor",
            )
            checked.append(result.as_dict())
    logger.info(f"post-deploy checks: {len(checked)} version(s)")
    return {"enabled": True, "checked": len(checked), "results": checked}


async def run_memory_consolidation(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Daily memory expiry + duplicate/contradiction pass (no silent merging)."""
    from app.services.memory_service import MemoryService

    async with get_session_factory()() as db:
        result = await MemoryService(db).consolidate_memories(dry_run=False)
    logger.info(f"memory consolidation: {result}")
    return result


class WorkerSettings:
    functions = [refresh_catalog, run_post_deploy_checks, run_memory_consolidation]
    cron_jobs = [
        cron(refresh_catalog, hour=3, minute=0),
        cron(run_post_deploy_checks, hour=4, minute=0),
        cron(run_memory_consolidation, hour=4, minute=30),
    ]
