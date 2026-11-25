"""Legal intelligence and government monitoring routes (OD-31).

Research and compliance assistance only. No route here creates legal authority
or makes a binding commitment on IAM's behalf.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.legal_service import LegalError, LegalService

router = APIRouter(prefix="/api/v1/legal", tags=["legal-intelligence"])


class SourceRequest(BaseModel):
    name: str
    jurisdiction: str
    authority_type: str
    url: str
    feed_url: Optional[str] = None
    reliability: str = "official"
    terms_url: Optional[str] = None


class InstrumentRequest(BaseModel):
    source_id: str
    jurisdiction: Optional[str] = None
    title: str
    authority_name: Optional[str] = None
    instrument_type: str = "announcement"
    status: str = "announcement"
    official_url: Optional[str] = None
    summary: Optional[str] = None
    published_at: Optional[str] = None
    effective_at: Optional[str] = None
    content: Optional[Dict[str, Any]] = None


class AmendmentRequest(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    severity: str = "important"
    reason: str = "new official version"


class ChangeRequest(BaseModel):
    instrument_id: str
    change_type: str = "new"
    severity: str = "informational"
    evidence: Dict[str, Any]


class UnderstandRequest(BaseModel):
    summary: str


class ImpactRequest(BaseModel):
    impacts: List[Dict[str, Any]]


class RecommendationRequest(BaseModel):
    recommendations: List[str]


class AuthoriseRequest(BaseModel):
    creator_approval_reference: str
    professional_review_reference: Optional[str] = None


class EvidenceRequest(BaseModel):
    evidence: Dict[str, Any]


class ObligationRequest(BaseModel):
    obligation_id: str
    status: str
    evidence: Dict[str, Any]


class CheckRequest(BaseModel):
    content: Optional[str] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _handle(exc: LegalError) -> HTTPException:
    status = 404 if "not found" in str(exc) else 400
    return HTTPException(status_code=status, detail=str(exc))


@router.post("/sources")
async def register_source(payload: SourceRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).register_source(payload.model_dump(), _actor(request))
    except LegalError as exc:
        raise _handle(exc)


@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db_session)):
    return await LegalService(db).sources()


@router.post("/sources/{source_id}/check")
async def check_source(source_id: str, payload: CheckRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).check_source(source_id, payload.content)
    except LegalError as exc:
        raise _handle(exc)


@router.post("/instruments")
async def record_instrument(payload: InstrumentRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).record_instrument(payload.model_dump(exclude_none=True), _actor(request))
    except LegalError as exc:
        raise _handle(exc)


@router.post("/instruments/{instrument_id}/amend")
async def amend_instrument(instrument_id: str, payload: AmendmentRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).amend_instrument(
            instrument_id, payload.model_dump(exclude_none=True), _actor(request)
        )
    except LegalError as exc:
        raise _handle(exc)


@router.post("/changes")
async def record_change(payload: ChangeRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).record_change(payload.model_dump(), _actor(request))
    except LegalError as exc:
        raise _handle(exc)


@router.post("/changes/{change_id}/authenticate")
async def authenticate(change_id: str, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).authenticate(change_id, _actor(request))
    except LegalError as exc:
        raise _handle(exc)


@router.post("/changes/{change_id}/understand")
async def understand(change_id: str, payload: UnderstandRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).understand(change_id, payload.summary, _actor(request))
    except LegalError as exc:
        raise _handle(exc)


@router.post("/changes/{change_id}/assess")
async def assess(change_id: str, payload: ImpactRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).assess(change_id, payload.impacts, _actor(request))
    except LegalError as exc:
        raise _handle(exc)


@router.post("/changes/{change_id}/recommend")
async def recommend(change_id: str, payload: RecommendationRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).recommend(change_id, payload.recommendations, _actor(request))
    except LegalError as exc:
        raise _handle(exc)


@router.post("/changes/{change_id}/authorise")
async def authorise(change_id: str, payload: AuthoriseRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).authorise(
            change_id,
            payload.creator_approval_reference,
            payload.professional_review_reference,
            _actor(request),
        )
    except LegalError as exc:
        raise _handle(exc)


@router.post("/changes/{change_id}/implement")
async def implement(change_id: str, payload: EvidenceRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).implement(change_id, payload.evidence, _actor(request))
    except LegalError as exc:
        raise _handle(exc)


@router.post("/changes/{change_id}/verify")
async def verify(change_id: str, payload: EvidenceRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).verify(change_id, payload.evidence, _actor(request))
    except LegalError as exc:
        raise _handle(exc)


@router.post("/impacts/{impact_id}/obligations")
async def update_obligation(impact_id: str, payload: ObligationRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await LegalService(db).update_obligation(
            impact_id, payload.obligation_id, payload.status, payload.evidence, _actor(request)
        )
    except LegalError as exc:
        raise _handle(exc)


@router.get("/alerts")
async def alerts(severity: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    return await LegalService(db).alerts(severity)


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db_session)):
    return await LegalService(db).status()
