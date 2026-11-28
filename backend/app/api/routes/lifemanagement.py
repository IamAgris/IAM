"""Life management routes - daily self-management and life history"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db_session
from app.services.lifemanagement_service import LifeManagementService

router = APIRouter(prefix="/api/v1/life", tags=["life-management"])


class CycleStateRequest(BaseModel):
    state: str  # idle, working, researching, learning, resting, conserving
    activities: Optional[List[str]] = None


class LifeHistoryRequest(BaseModel):
    event_type: str
    title: str
    description: Optional[str] = None
    significance: int = 5
    related_memory_ids: Optional[List[str]] = None
    related_goal_ids: Optional[List[str]] = None


@router.get("/cycle")
async def get_cycle(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get current life cycle state."""
    service = LifeManagementService(db)
    return await service.get_current_cycle()


@router.post("/cycle")
async def set_cycle_state(  # type: ignore[no-untyped-def]
    request: CycleStateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Set the current life cycle state."""
    service = LifeManagementService(db)
    try:
        return await service.set_cycle_state(request.state, request.activities)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/history")
async def record_life_history(  # type: ignore[no-untyped-def]
    request: LifeHistoryRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Record an important life event."""
    service = LifeManagementService(db)
    try:
        return await service.record_life_history(
            request.event_type,
            request.title,
            request.description,
            request.significance,
            request.related_memory_ids,
            request.related_goal_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history")
async def list_life_history(  # type: ignore[no-untyped-def]
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
):
    """Get chronological life history."""
    service = LifeManagementService(db)
    return await service.get_life_history(limit=limit)


@router.get("/goals/lifecycles")
async def get_goal_lifecycles(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get all goal lifecycle tracking."""
    service = LifeManagementService(db)
    return await service.get_goal_lifecycles()
