"""Verified social presence API (OD-30) — no live platform access."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.socialpresence_service import SocialPresenceError, SocialPresenceService

router = APIRouter(prefix="/api/v1/social", tags=["social-presence"])


class PresenceCreate(BaseModel):
    platform: str
    handle: str
    profile_url: str
    owner_entity: str
    approval_id: Optional[str] = None


class PresenceVerify(BaseModel):
    approval_id: str


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


@router.get("/presences")
async def list_presences(
    verified_only: bool = False,
    db: AsyncSession = Depends(get_db_session),
):
    return await SocialPresenceService(db).list(verified_only)


@router.post("/presences")
async def register_presence(
    payload: PresenceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await SocialPresenceService(db).register(
            platform=payload.platform,
            handle=payload.handle,
            profile_url=payload.profile_url,
            owner_entity=payload.owner_entity,
            approval_id=payload.approval_id,
            actor=_actor(request),
        )
    except SocialPresenceError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.post("/presences/{presence_id}/verify")
async def verify_presence(
    presence_id: str,
    payload: PresenceVerify,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await SocialPresenceService(db).verify(
            presence_id, payload.approval_id, _actor(request)
        )
    except SocialPresenceError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
