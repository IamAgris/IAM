"""Opt-in user email chat endpoints (OD-59 / Doc 39).

Lives under the public ``/api/v1/access`` prefix: visitors are anonymous and are
identified by their existing visitor token. The inbound forward is protected by
an HMAC over the raw body, not by a bearer credential. No endpoint here carries
Creator authority and no endpoint reads another visitor's conversation.
"""

import hashlib
import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict

from app.core.config import settings
from app.core.database import get_db_session
from app.services.globalaccess_service import GlobalAccessService
from app.services.user_email_service import UserEmailError, UserEmailService

router = APIRouter(prefix="/api/v1/access/user-email", tags=["user-email"])

SIGNATURE_HEADER = "X-User-Email-Signature"


def verify_webhook_signature(raw_body: bytes, provided: str, secret: str) -> bool:
    """HMAC-SHA256 over the raw body. Empty secret or signature never matches."""
    if not secret or not provided:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided)


class OptInRequest(BaseModel):
    visitor_token: str
    email: str


class VerifyRequest(BaseModel):
    visitor_token: str
    token: str


class OptOutRequest(BaseModel):
    visitor_token: str


class SendRequest(BaseModel):
    visitor_token: str
    content: str


class InboundRequest(BaseModel):
    message_id: str
    email: str
    subject: str = ""
    body: str


def _guard(error: UserEmailError) -> HTTPException:
    status = 503 if "disabled" in str(error) or "configured" in str(error) else 400
    return HTTPException(status_code=status, detail=str(error))


async def _visitor_id(visitor_token: str, db: AsyncSession) -> str:
    if not visitor_token or not visitor_token.strip():
        raise HTTPException(status_code=400, detail="visitor_token is required")
    visitor = await GlobalAccessService(db).create_or_get_visitor(visitor_token.strip())
    return str(visitor["id"])


@router.post("/opt-in")
async def opt_in(request: OptInRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """Start opt-in; a single-use verification token is emailed to the user."""
    try:
        visitor_id = await _visitor_id(request.visitor_token, db)
        return await UserEmailService(db).opt_in(visitor_id, request.email)
    except UserEmailError as exc:
        raise _guard(exc) from exc


@router.post("/verify")
async def verify(request: VerifyRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """Complete opt-in with the emailed token. Verified address is not authority."""
    try:
        visitor_id = await _visitor_id(request.visitor_token, db)
        return await UserEmailService(db).verify(visitor_id, request.token)
    except UserEmailError as exc:
        raise _guard(exc) from exc


@router.get("/status")
async def status(visitor_token: str, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    try:
        visitor_id = await _visitor_id(visitor_token, db)
        return await UserEmailService(db).status(visitor_id)
    except UserEmailError as exc:
        raise _guard(exc) from exc


@router.post("/opt-out")
async def opt_out(request: OptOutRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    try:
        visitor_id = await _visitor_id(request.visitor_token, db)
        return await UserEmailService(db).opt_out(visitor_id)
    except UserEmailError as exc:
        raise _guard(exc) from exc


@router.post("/send")
async def send_message(request: SendRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """Send one IAM reply, stored only in this visitor's private thread."""
    try:
        visitor_id = await _visitor_id(request.visitor_token, db)
        return await UserEmailService(db).send_message(visitor_id, request.content)
    except UserEmailError as exc:
        raise _guard(exc) from exc


@router.post("/inbound")
async def inbound(http_request: Request, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """HMAC-protected forwarding endpoint for provider-delivered user replies."""
    secret = os.environ.get(settings.user_email_webhook_secret_env, "")
    if not secret:
        raise HTTPException(status_code=503, detail="User email webhook is not configured")
    raw = await http_request.body()
    provided = http_request.headers.get(SIGNATURE_HEADER, "")
    if not verify_webhook_signature(raw, provided, secret):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")
    try:
        payload = InboundRequest.model_validate_json(raw)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid inbound payload") from exc
    try:
        return await UserEmailService(db).receive(payload.model_dump())
    except UserEmailError as exc:
        raise _guard(exc) from exc
