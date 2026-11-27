"""OD-52 scheduled model-catalogue refresh on the existing OD-08 ARQ runtime.

    docker compose --profile catalog-arq up -d

Discovery, metadata refresh and availability checks are no-ops unless their
OD-52 flags are enabled, so this worker is safe to deploy before confirmation.
"""

from __future__ import annotations

from typing import Any, Dict

import loguru
from arq import cron

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


class WorkerSettings:
    functions = [refresh_catalog]
    cron_jobs = [cron(refresh_catalog, hour=3, minute=0)]
