"""OD-52 Phase B: dual-source model discovery endpoints."""

from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.intel_router_service import IntelligenceRouter
from app.services.model_discovery import ModelDiscoveryService

router = APIRouter(prefix="/api/v1/models/discovery", tags=["model-discovery"])


@router.post("/{provider}")
async def discover(
    provider: str, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Discover models from NVIDIA's catalogue and Models.dev metadata.

    Results are registry entries — not proof of a working free endpoint.
    Endpoint availability is checked by the Phase D monitor.
    """
    await IntelligenceRouter(db).initialize_providers()  # type: ignore[no-untyped-call]
    service = ModelDiscoveryService(db)
    models = await service.discover(provider)
    return {
        "provider": provider,
        "models": models,
        "count": len(models),
        "registration": service.registration,
        "claim": "catalogue metadata only; endpoint availability not verified",
    }
