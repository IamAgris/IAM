"""Website Consent API routes (Privacy & Data Governance)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.web_consent_service import (
    WebsiteConsentError,
    WebsiteConsentService,
)

router = APIRouter(prefix="/api/v1/web/consent", tags=["web-consent"])


class ConsentCreate(BaseModel):
    website_knowledge_id: str
    cookie_categories: List[str] = Field(default_factory=list)
    consent_status: str = "pending"
    data_retention_preference: Optional[str] = None
    sensitive_info_classification: Optional[str] = None
    gdpr_applicable: bool = False
    ccpa_applicable: bool = False


class ConsentUpdate(BaseModel):
    consent_status: Optional[str] = None
    cookie_categories: Optional[List[str]] = None
    data_retention_preference: Optional[str] = None
    sensitive_info_classification: Optional[str] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _fail(exc: WebsiteConsentError) -> HTTPException:
    return HTTPException(400, str(exc))


@router.post("")
async def create_consent(  # type: ignore[no-untyped-def]
    payload: ConsentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Create website consent record."""
    try:
        return await WebsiteConsentService(db).create(
            website_knowledge_id=payload.website_knowledge_id,
            cookie_categories=payload.cookie_categories,
            consent_status=payload.consent_status,
            data_retention_preference=payload.data_retention_preference,
            sensitive_info_classification=payload.sensitive_info_classification,
            gdpr_applicable=payload.gdpr_applicable,
            ccpa_applicable=payload.ccpa_applicable,
            actor=_actor(request),
        )
    except WebsiteConsentError as exc:
        raise _fail(exc) from exc


@router.get("")
async def list_consents(  # type: ignore[no-untyped-def]
    website_knowledge_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List website consent records."""
    return await WebsiteConsentService(db).list(website_knowledge_id)


@router.get("/{consent_id}")
async def get_consent(consent_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get a single website consent record by ID."""
    try:
        return await WebsiteConsentService(db).get(consent_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.patch("/{consent_id}")
async def update_consent(  # type: ignore[no-untyped-def]
    consent_id: str,
    payload: ConsentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Update website consent."""
    try:
        return await WebsiteConsentService(db).update_consent(
            consent_id,
            consent_status=payload.consent_status,
            cookie_categories=payload.cookie_categories,
            data_retention_preference=payload.data_retention_preference,
            sensitive_info_classification=payload.sensitive_info_classification,
            actor=_actor(request),
        )
    except WebsiteConsentError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/{consent_id}")
async def delete_consent(  # type: ignore[no-untyped-def]
    consent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete website consent record."""
    try:
        return await WebsiteConsentService(db).delete(consent_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc