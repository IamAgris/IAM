"""Model provider and intelligence router routes.

NVIDIA is one provider; IAM remains independent of any single provider.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db_session
from app.services.intel_router_service import IntelligenceRouter
from app.services.model_policy import ModelPolicyDenied, PAID_ACTION, require_authorization

router = APIRouter(prefix="/api/v1/models/router", tags=["model-router"])


class SelectRequest(BaseModel):
    task_type: str
    required_capabilities: Optional[List[str]] = None
    prefer_provider: Optional[str] = None
    allow_paid: bool = False
    task_complexity: Optional[int] = None
    available_aliases: Optional[List[str]] = None


@router.post("/initialize")
async def initialize(db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Register known model providers."""
    service = IntelligenceRouter(db)
    await service.initialize_providers()  # type: ignore[no-untyped-call]
    return {"status": "initialized"}


@router.post("/discover/nvidia")
async def discover_nvidia(db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Discover available models from NVIDIA's catalogue.
    Free-only mode is respected; choices come from the catalogue, not a hardcoded list.
    """
    service = IntelligenceRouter(db)
    models = await service.discover_nvidia_models()
    return {"provider": "nvidia", "models": models, "count": len(models)}


@router.get("/providers")
async def list_providers(db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """List registered model providers."""
    service = IntelligenceRouter(db)
    return await service.list_providers()


@router.get("/models")
async def list_models(provider: Optional[str] = None, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """List discovered models, optionally filtered by provider."""
    service = IntelligenceRouter(db)
    return await service.list_models(provider)


@router.post("/select")
async def select_model(request: SelectRequest, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Select the best model for a task by capability, quality, cost and availability."""
    if request.allow_paid:
        try:
            await require_authorization(db, PAID_ACTION)
        except ModelPolicyDenied as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    service = IntelligenceRouter(db)
    return await service.select_model(
        request.task_type,
        request.required_capabilities,
        request.prefer_provider,
        request.allow_paid,
        task_complexity=request.task_complexity,
        available_aliases=(
            set(request.available_aliases) if request.available_aliases is not None else None
        ),
    )


@router.get("/history")
async def get_history(limit: int = 50, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get routing decision history."""
    service = IntelligenceRouter(db)
    return await service.get_routing_history(limit)
