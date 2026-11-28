"""Digital Reputation & Trust API routes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.digital_reputation_service import (
    DigitalReputationError,
    DigitalReputationService,
)

router = APIRouter(prefix="/api/v1/web/reputation", tags=["web-reputation"])


class ReputationCreate(BaseModel):
    website_knowledge_id: str
    account_username: str
    verification_status: str = "unverified"
    platform_warnings: List[Dict[str, Any]] = Field(default_factory=list)
    suspensions: List[Dict[str, Any]] = Field(default_factory=list)
    restrictions: List[Dict[str, Any]] = Field(default_factory=list)
    tos_changes: List[Dict[str, Any]] = Field(default_factory=list)
    privacy_changes: List[Dict[str, Any]] = Field(default_factory=list)
    service_reliability_score: int = Field(default=50, ge=0, le=100)
    account_security_score: int = Field(default=50, ge=0, le=100)
    identity_consistency_score: int = Field(default=50, ge=0, le=100)
    ownership_evidence: List[Dict[str, Any]] = Field(default_factory=list)


class WarningCreate(BaseModel):
    warning: Dict[str, Any]


class SuspensionCreate(BaseModel):
    suspension: Dict[str, Any]


class TosChangeCreate(BaseModel):
    change: Dict[str, Any]


class PrivacyChangeCreate(BaseModel):
    change: Dict[str, Any]


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _fail(exc: DigitalReputationError) -> HTTPException:
    return HTTPException(400, str(exc))


@router.post("")
async def create_reputation(  # type: ignore[no-untyped-def]
    payload: ReputationCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a digital reputation record for a website account."""
    try:
        return await DigitalReputationService(db).create(
            website_knowledge_id=payload.website_knowledge_id,
            account_username=payload.account_username,
            verification_status=payload.verification_status,
            platform_warnings=payload.platform_warnings,
            suspensions=payload.suspensions,
            restrictions=payload.restrictions,
            tos_changes=payload.tos_changes,
            privacy_changes=payload.privacy_changes,
            service_reliability_score=payload.service_reliability_score,
            account_security_score=payload.account_security_score,
            identity_consistency_score=payload.identity_consistency_score,
            ownership_evidence=payload.ownership_evidence,
            actor=_actor(request),
        )
    except DigitalReputationError as exc:
        raise _fail(exc) from exc


@router.get("")
async def list_reputations(  # type: ignore[no-untyped-def]
    website_knowledge_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List digital reputation records."""
    return await DigitalReputationService(db).list(website_knowledge_id)


@router.get("/{reputation_id}")
async def get_reputation(reputation_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get a single digital reputation record by ID."""
    try:
        return await DigitalReputationService(db).get(reputation_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{reputation_id}/warnings")
async def add_platform_warning(  # type: ignore[no-untyped-def]
    reputation_id: str,
    payload: WarningCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Add a platform warning to the reputation record."""
    try:
        return await DigitalReputationService(db).update_platform_warning(
            reputation_id, payload.warning, _actor(request)
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{reputation_id}/suspensions")
async def add_suspension(  # type: ignore[no-untyped-def]
    reputation_id: str,
    payload: SuspensionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Record a suspension event for the account."""
    try:
        return await DigitalReputationService(db).record_suspension(
            reputation_id, payload.suspension, _actor(request)
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{reputation_id}/tos-changes")
async def add_tos_change(  # type: ignore[no-untyped-def]
    reputation_id: str,
    payload: TosChangeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Record a Terms of Service change affecting the account."""
    try:
        return await DigitalReputationService(db).record_tos_change(
            reputation_id, payload.change, _actor(request)
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{reputation_id}/privacy-changes")
async def add_privacy_change(  # type: ignore[no-untyped-def]
    reputation_id: str,
    payload: PrivacyChangeCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Record a privacy policy change affecting the account."""
    try:
        return await DigitalReputationService(db).record_privacy_change(
            reputation_id, payload.change, _actor(request)
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc