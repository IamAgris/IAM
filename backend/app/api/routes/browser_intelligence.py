"""Browser Intelligence API — page understanding, extraction and tab coordination (Doc 29 P2)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.browser_intelligence_service import (
    BrowserIntelligenceError,
    BrowserIntelligenceService,
)
from app.services.browser_document_service import (
    BrowserDocumentService,
    DocumentParsingError,
)
from app.services.browser_evidence_service import BrowserEvidenceError

router = APIRouter(prefix="/api/v1/browser/intelligence", tags=["browser-intelligence"])


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "sdk") if credential else "sdk"


def _actor_type(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    if credential and str(credential.get("actor_type", "")) == "creator":
        return "creator"
    return "agent"


class UnderstandRequest(BaseModel):
    session_token: str
    task_id: Optional[str] = None
    actor: Optional[str] = None
    actor_type: str = "agent"


class ExtractRequest(BaseModel):
    session_token: str
    kind: str = "auto"
    task_id: Optional[str] = None
    actor: Optional[str] = None
    actor_type: str = "agent"


class VerifyRequest(BaseModel):
    session_token: str
    expected: Dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[str] = None
    actor: Optional[str] = None
    actor_type: str = "agent"


class DocumentRequest(BaseModel):
    url: str
    task_id: Optional[str] = None
    actor: Optional[str] = None
    actor_type: str = "agent"


class TabAction(BaseModel):
    action: str
    target: str = ""
    value: Optional[str] = None
    tab_id: Optional[str] = None
    new_tab: bool = False


class CoordinateRequest(BaseModel):
    session_token: str
    actions: List[TabAction] = Field(min_length=1)
    task_id: Optional[str] = None
    actor: Optional[str] = None
    actor_type: str = "agent"


@router.post("/understand")
async def understand(
    payload: UnderstandRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserIntelligenceService(db).understand(
            payload.session_token,
            task_id=payload.task_id,
            actor=payload.actor or _actor(request),
            actor_type=payload.actor_type,
        )
    except BrowserIntelligenceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/extract")
async def extract(
    payload: ExtractRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserIntelligenceService(db).extract(
            payload.session_token,
            payload.kind,
            task_id=payload.task_id,
            actor=payload.actor or _actor(request),
            actor_type=payload.actor_type,
        )
    except (BrowserIntelligenceError, BrowserEvidenceError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/verify")
async def verify_extraction(
    payload: VerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserIntelligenceService(db).verify_extraction(
            payload.session_token,
            payload.expected,
            task_id=payload.task_id,
            actor=payload.actor or _actor(request),
            actor_type=payload.actor_type,
        )
    except (BrowserIntelligenceError, BrowserEvidenceError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/document")
async def parse_document(
    payload: DocumentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserDocumentService(db).parse_url(
            payload.url,
            task_id=payload.task_id,
            actor=payload.actor or _actor(request),
            actor_type=payload.actor_type,
        )
    except (DocumentParsingError, BrowserEvidenceError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/tabs/coordinate")
async def coordinate_tabs(
    payload: CoordinateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserIntelligenceService(db).coordinate_tabs(
            payload.session_token,
            [action.model_dump() for action in payload.actions],
            task_id=payload.task_id,
            actor=payload.actor or _actor(request),
            actor_type=payload.actor_type,
        )
    except (BrowserIntelligenceError, BrowserEvidenceError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
