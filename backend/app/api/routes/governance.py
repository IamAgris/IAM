"""Governance engine routes - authority boundaries and security"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Dict, Any

from app.core.database import get_db_session
from app.services.governance_service import GovernanceService

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


class AuthorityCheckRequest(BaseModel):
    action_type: str
    requested_level: str  # 1, 2, 3, 4


@router.get("/boundaries")
async def get_authority_boundaries(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get all authority level definitions."""
    service = GovernanceService(db)
    return await service.get_authority_boundaries()


@router.post("/check-authority")
async def check_authority(  # type: ignore[no-untyped-def]
    request: AuthorityCheckRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Check if an action at the requested authority level is permitted."""
    service = GovernanceService(db)
    return await service.check_authority(request.action_type, request.requested_level)


@router.get("/security-boundaries")
async def get_security_boundaries(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get security boundaries IAM cannot cross."""
    service = GovernanceService(db)
    return await service.get_security_boundaries()


@router.post("/initialize")
async def initialize_governance(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Initialize default authority and security boundaries."""
    service = GovernanceService(db)
    await service.initialize_default_boundaries()  # type: ignore[no-untyped-call]
    return {"status": "initialized"}
