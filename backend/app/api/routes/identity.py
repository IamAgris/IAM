"""Identity routes - AI digital identity management with database persistence"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db_session
from app.services.identity_service import IdentityService

router = APIRouter(prefix="/api/v1/identity", tags=["identity"])


# --- Pydantic models ---

class IdentityCreate(BaseModel):
    name: str
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    communication_preferences: Dict[str, Any] = {}
    interests: List[str] = []
    personal_goals: List[str] = []


class IdentityUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    avatar_url: Optional[str] = None
    communication_preferences: Optional[Dict[str, Any]] = None
    interests: Optional[List[str]] = None
    personal_goals: Optional[List[str]] = None
    reason: Optional[str] = None


class IdentityResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    avatar_url: Optional[str]
    communication_preferences: Dict[str, Any]
    interests: List[str]
    personal_goals: List[str]
    created_at: Optional[str]
    updated_at: Optional[str]


# --- Routes ---

@router.get("/", response_model=Optional[IdentityResponse])
async def get_identity(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get the AI's current identity from the database."""
    service = IdentityService(db)
    identity = await service.get_identity()
    if not identity:
        return None
    return identity


@router.post("/", response_model=IdentityResponse)
async def create_identity(  # type: ignore[no-untyped-def]
    identity: IdentityCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Initialize the AI's digital identity (Phase 1)."""
    service = IdentityService(db)
    try:
        return await service.create_identity({
            "name": identity.name,
            "description": identity.description,
            "avatar_url": identity.avatar_url,
            "communication_preferences": identity.communication_preferences,
            "interests": identity.interests,
            "personal_goals": identity.personal_goals,
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/", response_model=IdentityResponse)
async def update_identity(  # type: ignore[no-untyped-def]
    changes: IdentityUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update the AI's identity and record the change in history."""
    # Get current identity to find its ID
    service = IdentityService(db)
    current = await service.get_identity()
    if not current:
        raise HTTPException(status_code=404, detail="Identity not found. Create one first.")

    change_dict = changes.model_dump(exclude_unset=True, exclude={"reason"})
    reason = changes.reason or "Identity update"

    try:
        return await service.update_identity(current["id"], {**change_dict, "reason": reason})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history")
async def get_identity_history(  # type: ignore[no-untyped-def]
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
):
    """Get identity change history."""
    service = IdentityService(db)
    return await service.get_history(limit=limit)
