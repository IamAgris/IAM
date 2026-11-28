"""IAM-initiated Creator communication endpoints (OD-18 / OD-19).

Questions/status updates are informational. Only /api/v1/creator/requests plus a
verified signature can grant authority; these endpoints never do.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from app.core.config import settings
from app.core.database import get_db_session
from app.services.creator_communication import (
    CreatorCommunicationError,
    CreatorCommunicationService,
)
from app.services.creator_gateway import (
    CREATOR_SIGNATURE_HEADER,
    verify_gateway_signature,
)

router = APIRouter(prefix="/api/v1/creator/messages", tags=["creator-communication"])


class QuestionRequest(BaseModel):
    question: str
    context: Optional[str] = None
    reason: Optional[str] = None


class StatusRequest(BaseModel):
    update: str
    context: Optional[str] = None


class ReplyRequest(BaseModel):
    body: str


def _handle(exc: Exception):  # type: ignore[no-untyped-def]
    raise HTTPException(status_code=400, detail=str(exc))


@router.post("/questions", status_code=202)
async def ask_creator(request: QuestionRequest, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Send an informational question to the Creator by email."""
    try:
        return await CreatorCommunicationService(db).ask(
            request.question, context=request.context, reason=request.reason
        )
    except CreatorCommunicationError as exc:
        _handle(exc)


@router.post("/status", status_code=202)
async def send_status(request: StatusRequest, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Send an informational progress update to the Creator by email."""
    try:
        return await CreatorCommunicationService(db).send_status(
            request.update, context=request.context
        )
    except CreatorCommunicationError as exc:
        _handle(exc)


@router.get("")
async def list_messages(limit: int = 50, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """List IAM↔Creator messages with authority markers."""
    return await CreatorCommunicationService(db).list_messages(limit)


@router.post("/replies", status_code=202)
async def record_reply(request: Request, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Gateway callback for a Creator reply. Informational, never authority."""
    secret = settings.creator_gateway_secret
    if not secret:
        raise HTTPException(status_code=503, detail="Creator gateway is not configured")
    raw = await request.body()
    if not verify_gateway_signature(raw, request.headers.get(CREATOR_SIGNATURE_HEADER, ""), secret):
        raise HTTPException(status_code=403, detail="Invalid gateway signature")
    try:
        payload = await request.json()
        return await CreatorCommunicationService(db).record_reply(
            str(payload.get("message_id", "")), str(payload.get("body", ""))
        )
    except CreatorCommunicationError as exc:
        _handle(exc)
