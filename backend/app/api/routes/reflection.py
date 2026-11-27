"""Reflection engine routes - reviewing decisions and experiences"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db_session
from app.services.reflection_service import ReflectionService

router = APIRouter(prefix="/api/v1/reflection", tags=["reflection"])


class ReflectionRequest(BaseModel):
    reflection_type: str  # decision, experience, outcome, principle
    title: str
    content: str
    lesson_learned: Optional[str] = None
    confidence: float = 0.5
    related_decision_ids: Optional[List[str]] = None
    related_memory_ids: Optional[List[str]] = None


class PrincipleUpdateRequest(BaseModel):
    principle_statement: Optional[str] = None


@router.post("")
async def create_reflection(request: ReflectionRequest, db: AsyncSession = Depends(get_db_session)):
    """Create a reflection entry."""
    service = ReflectionService(db)
    try:
        return await service.create_reflection(
            request.reflection_type, request.title, request.content,
            request.lesson_learned, request.confidence,
            request.related_decision_ids, request.related_memory_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_reflections(limit: int = 50, db: AsyncSession = Depends(get_db_session)):
    """List reflection entries."""
    service = ReflectionService(db)
    return await service.list_reflections(limit=limit)


@router.get("/principles")
async def get_operating_principles(db: AsyncSession = Depends(get_db_session)):
    """Get IAM's operating principles."""
    service = ReflectionService(db)
    return await service.get_operating_principles()


@router.patch("/principles/{principle_id}")
async def update_principle(
    principle_id: str,
    request: PrincipleUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Update an operating principle (immutable ones cannot be changed by IAM)."""
    from app.services.constitutional_policy import (
        ConstitutionalPolicyDenied,
        assert_allowed,
    )

    try:
        await assert_allowed(db, "constitution_change")
    except ConstitutionalPolicyDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    service = ReflectionService(db)
    try:
        return await service.update_operating_principle(principle_id, request.principle_statement)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/initialize")
async def initialize_principles(db: AsyncSession = Depends(get_db_session)):
    """Initialize default operating principles."""
    service = ReflectionService(db)
    await service.initialize_default_principles()
    return {"status": "initialized"}
