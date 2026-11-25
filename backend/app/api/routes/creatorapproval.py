"""Creator approval by email — request delivery and signed decision gateway.

OD-19: there is no Creator dashboard in the frontend. These endpoints are the
backend integration points for IAM's Creator email channel and the external
hardware signer. They are not a user-facing approval UI.
"""

from typing import Any, Callable, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.services.creator_gateway import (
    CREATOR_SIGNATURE_HEADER,
    DecisionGatewayRequest,
    verify_gateway_signature,
)
from app.services.creatorapproval_service import (
    CreatorApprovalError,
    CreatorApprovalService,
)

router = APIRouter(prefix="/api/v1/creator", tags=["creator-approval-email"])


class RequestCreate(BaseModel):
    action_type: str
    summary: str
    consequences: List[str] = Field(default_factory=list)
    risk_level: str = "3"
    target_ref: Optional[str] = None
    reason: Optional[str] = None
    channel: str = "creator_email"  # creator_email | creator_cli | creator_webhook | creator_node | creator_file


class DecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    signature: str
    signer_id: str


async def _run(operation: Callable, *args: Any, **kwargs: Any) -> Any:
    try:
        return await operation(*args, **kwargs)
    except CreatorApprovalError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/policy")
async def policy():
    return {
        "channel": "creator_email",
        "creator_ui": False,
        "plain_email_reply_authorises": False,
        "authority": "ED25519 signature over sha256(canonical challenge)|decision",
        "signer": "external hardware signer (OD-03)",
        "email_transport": settings.creator_email_transport,
        "gateway_configured": bool(settings.creator_gateway_secret),
    }


@router.post("/requests", status_code=202)
async def create_request(
    request: RequestCreate, db: AsyncSession = Depends(get_db_session)
):
    """IAM creates an approval request; the returned package is sent by email."""
    return await _run(
        CreatorApprovalService(db).create_request,
        action_type=request.action_type,
        summary=request.summary,
        consequences=request.consequences,
        risk_level=request.risk_level,
        target_ref=request.target_ref,
        reason=request.reason,
        channel=request.channel,
    )


@router.get("/requests")
async def list_requests(
    status: Optional[str] = None, db: AsyncSession = Depends(get_db_session)
):
    return await _run(CreatorApprovalService(db).list_requests, status)


@router.get("/requests/{request_id}")
async def get_request(request_id: str, db: AsyncSession = Depends(get_db_session)):
    return await _run(CreatorApprovalService(db).get_request, request_id)


@router.post("/requests/{request_id}/decide")
async def decide(
    request_id: str,
    request: DecisionRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Inbound gateway for a signed decision returned by the Creator signer.

    This is not a UI action: the signature is verified against the configured
    Creator public key and one-time challenge hash before any authority exists.
    """
    return await _run(
        CreatorApprovalService(db).decide,
        request_id,
        decision=request.decision,
        signature=request.signature,
        signer_id=request.signer_id,
    )


@router.post("/gateway/decision")
async def gateway_decision(
    request: Request, db: AsyncSession = Depends(get_db_session)
):
    """Inbound webhook for the Creator email/signer gateway.

    Two independent checks: HMAC over the raw body proves the callback came from
    the configured gateway; the ED25519 signature proves the Creator approved.
    A plain email reply cannot reach this path.
    """
    secret = settings.creator_gateway_secret
    if not secret:
        raise HTTPException(status_code=503, detail="Creator gateway is not configured")
    raw = await request.body()
    if not verify_gateway_signature(
        raw, request.headers.get(CREATOR_SIGNATURE_HEADER, ""), secret
    ):
        raise HTTPException(status_code=403, detail="Invalid gateway signature")
    try:
        payload = DecisionGatewayRequest.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = await _run(
        CreatorApprovalService(db).decide,
        payload.request_id,
        decision=payload.decision,
        signature=payload.signature,
        signer_id=payload.signer_id,
    )
    return result


@router.get("/requests/{request_id}/challenge")
async def challenge_for_signer(
    request_id: str, db: AsyncSession = Depends(get_db_session)
):
    """Challenge material for the external signer — contains no private key."""
    return await _run(
        CreatorApprovalService(db).challenge_for_signer, request_id
    )


@router.post("/requests/{request_id}/deliver")
async def deliver_request(
    request_id: str, db: AsyncSession = Depends(get_db_session)
):
    """Retry delivery of a queued Creator approval email."""
    return await _run(CreatorApprovalService(db).deliver_request, request_id)


@router.get("/outbox")
async def outbox(db: AsyncSession = Depends(get_db_session)):
    return await _run(CreatorApprovalService(db).outbox)


@router.get("/outbox/dead-letters")
async def dead_letters(db: AsyncSession = Depends(get_db_session)):
    return await _run(CreatorApprovalService(db).dead_letters)


@router.post("/outbox/retry")
async def retry_outbox(db: AsyncSession = Depends(get_db_session)):
    """Worker-friendly retry of all pending/failed email deliveries."""
    return await _run(CreatorApprovalService(db).retry_failed_deliveries)


@router.get("/audit")
async def audit(
    request_id: Optional[str] = None, db: AsyncSession = Depends(get_db_session)
):
    return await _run(CreatorApprovalService(db).audit, request_id)


@router.post("/authorizations/{authorization_id}/revoke")
async def revoke(
    authorization_id: str, db: AsyncSession = Depends(get_db_session)
):
    return {
        "revoked": await _run(
            CreatorApprovalService(db).revoke_authorization, authorization_id
        )
    }
