"""Digital Security Incident API routes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.digital_security_service import (
    DigitalSecurityIncidentError,
    DigitalSecurityService,
)

router = APIRouter(prefix="/api/v1/web/security-incidents", tags=["security-incidents"])


class IncidentCreate(BaseModel):
    website_knowledge_id: str
    incident_type: str
    title: str
    description: Optional[str] = None
    severity: str = "medium"
    affected_accounts: List[str] = Field(default_factory=list)
    remediation_actions: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)


class IncidentStatusUpdate(BaseModel):
    status: str


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _fail(exc: DigitalSecurityIncidentError) -> HTTPException:
    return HTTPException(400, str(exc))


@router.post("")
async def create_incident(  # type: ignore[no-untyped-def]
    payload: IncidentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a digital security incident record."""
    try:
        return await DigitalSecurityService(db).create(
            website_knowledge_id=payload.website_knowledge_id,
            incident_type=payload.incident_type,
            title=payload.title,
            description=payload.description,
            severity=payload.severity,
            affected_accounts=payload.affected_accounts,
            remediation_actions=payload.remediation_actions,
            evidence=payload.evidence,
            actor=_actor(request),
        )
    except DigitalSecurityIncidentError as exc:
        raise _fail(exc) from exc


@router.get("")
async def list_incidents(  # type: ignore[no-untyped-def]
    website_knowledge_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List digital security incident records."""
    return await DigitalSecurityService(db).list(website_knowledge_id)


@router.get("/{incident_id}")
async def get_incident(incident_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get a single security incident by ID."""
    try:
        return await DigitalSecurityService(db).get(incident_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.patch("/{incident_id}/status")
async def update_status(  # type: ignore[no-untyped-def]
    incident_id: str,
    payload: IncidentStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Update incident status."""
    try:
        return await DigitalSecurityService(db).update_status(
            incident_id, status=payload.status, actor=_actor(request)
        )
    except DigitalSecurityIncidentError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc