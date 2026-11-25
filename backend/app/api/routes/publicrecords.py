"""Public records, vital events and estate research routes (OD-30).

Evidence-based, dated, traceable and correctable. Access controls and privacy
boundaries are enforced before any record is accepted.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.publicrecords_service import PublicRecordsError, PublicRecordsService

router = APIRouter(prefix="/api/v1/public-records", tags=["public-records"])


class SourceRequest(BaseModel):
    name: str
    jurisdiction: str
    category: str
    url: str
    access_condition: str = "public"
    reliability: str = "unverified"
    terms_url: Optional[str] = None
    last_verified_at: Optional[str] = None


class RecordRequest(BaseModel):
    source_id: str
    category: Optional[str] = None
    jurisdiction: Optional[str] = None
    subject_name: Optional[str] = None
    title: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: Optional[str] = None
    source_url: Optional[str] = None
    facts: Dict[str, Any] = {}
    status: str = "uncertain"
    confidence: float = 0.5
    legal_authority_reference: Optional[str] = None
    is_statistical: bool = False


class CrossReferenceRequest(BaseModel):
    other_id: str
    relation_type: str
    evidence: Dict[str, Any]
    confidence: float = 0.5


class CorrectionRequest(BaseModel):
    facts: Dict[str, Any]
    reason: str
    status: str = "verified"
    confidence: float = 0.9


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


@router.post("/sources")
async def register_source(
    payload: SourceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PublicRecordsService(db).register_source(payload.model_dump(), _actor(request))
    except PublicRecordsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db_session)):
    return await PublicRecordsService(db).sources()


@router.post("/records")
async def ingest_record(
    payload: RecordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PublicRecordsService(db).ingest(payload.model_dump(exclude_none=True), _actor(request))
    except PublicRecordsError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/records")
async def search_records(
    category: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    subject_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
):
    return await PublicRecordsService(db).search(
        {
            "category": category,
            "jurisdiction": jurisdiction,
            "subject_name": subject_name,
            "status": status,
            "limit": limit,
        }
    )


@router.post("/records/{record_id}/cross-reference")
async def cross_reference(
    record_id: str,
    payload: CrossReferenceRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PublicRecordsService(db).cross_reference(
            record_id,
            payload.other_id,
            payload.relation_type,
            payload.evidence,
            payload.confidence,
            _actor(request),
        )
    except PublicRecordsError as exc:
        status = 404 if "not found" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc))


@router.post("/records/{record_id}/corrections")
async def correct_record(
    record_id: str,
    payload: CorrectionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PublicRecordsService(db).correct(
            record_id,
            payload.facts,
            payload.reason,
            payload.status,
            payload.confidence,
            _actor(request),
        )
    except PublicRecordsError as exc:
        status = 404 if "not found" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc))


@router.get("/records/{record_id}/relationships")
async def relationships(
    record_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PublicRecordsService(db).relationships(record_id)
    except PublicRecordsError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db_session)):
    return await PublicRecordsService(db).status()
