"""Capability registry routes - measurable skills and abilities"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db_session
from app.services.capability_service import CapabilityService

router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])


@router.get("/modules")
async def list_dispatchable_modules() -> Dict[str, Any]:
    """Discover the modules the autonomy loop may dispatch, with their contract."""
    from app.services.module_registry import discover

    modules = discover()
    return {"modules": modules, "count": len(modules)}


class CapabilityRequest(BaseModel):
    name: str
    category: str
    description: Optional[str] = None
    target_proficiency: int = 100


class AssessmentRequest(BaseModel):
    capability_id: str
    proficiency_level: int
    assessment_method: str  # test, project, simulation, review
    evidence: Optional[List[Dict[str, Any]]] = None
    assessor: Optional[str] = None


class LearningPathRequest(BaseModel):
    capability_id: str
    steps: List[Dict[str, Any]]


@router.post("")
async def create_capability(request: CapabilityRequest, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Define a new capability."""
    service = CapabilityService(db)
    try:
        return await service.create_capability(
            request.name, request.category, request.description, request.target_proficiency,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_capabilities(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """List all capabilities with current proficiency."""
    service = CapabilityService(db)
    return await service.list_capabilities()


@router.post("/assess")
async def assess_capability(request: AssessmentRequest, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Record a measurable capability assessment."""
    service = CapabilityService(db)
    try:
        return await service.assess_capability(
            request.capability_id, request.proficiency_level,
            request.assessment_method, request.evidence, request.assessor,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/learning-path")
async def create_learning_path(request: LearningPathRequest, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Create a planned learning journey."""
    service = CapabilityService(db)
    return await service.create_learning_path(request.capability_id, request.steps)
