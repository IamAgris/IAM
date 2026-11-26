"""Creator approval service — email carrier, signed challenge authority.

OD-18/OD-19: there is no Creator dashboard. IAM sends an explanatory approval
request to the verified Creator email address. A plain reply is never authority;
only a valid ED25519 signature from the Creator's external signer over the
one-time challenge hash is accepted.
"""

import base64
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
import loguru
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.creatorapproval import (
    CommunicationAudit,
    CreatorApproval,
    CreatorAuthorization,
    CreatorEmailDeadLetter,
    CreatorEmailOutbox,
    CreatorRequest,
    SignedChallenge,
)
from app.services.creator_email import transport_from_settings

LEVEL_ORDER = {"1": 1, "2": 2, "3": 3, "4": 4}


class CreatorApprovalError(PermissionError):
    """Raised when an approval request or signature is invalid."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def canonical_payload(payload: Dict[str, Any]) -> bytes:
    """Deterministic bytes that the Creator's signer signs over (via its hash)."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def hash_payload(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_payload(payload)).hexdigest()


def _public_key() -> Ed25519PublicKey:
    raw = settings.creator_public_key
    if not raw:
        raise CreatorApprovalError(
            "Creator public key is not configured; signed approvals cannot be verified"
        )
    try:
        if "-----BEGIN" in raw:
            key = serialization.load_pem_public_key(raw.encode("utf-8"))
        else:
            key = Ed25519PublicKey.from_public_bytes(base64.b64decode(raw, validate=True))
    except Exception as exc:
        raise CreatorApprovalError("Creator public key is invalid") from exc
    if not isinstance(key, Ed25519PublicKey):
        raise CreatorApprovalError("Creator public key must be ED25519")
    return key


class CreatorApprovalService:
    """Creates email approval requests and verifies signed decisions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ helpers

    async def _request(self, request_id: str) -> CreatorRequest:
        result = await self.db.execute(
            select(CreatorRequest).where(CreatorRequest.request_id == request_id)
        )
        request = result.scalar_one_or_none()
        if not request:
            raise LookupError(f"Creator request not found: {request_id}")
        return request

    async def _audit(
        self,
        *,
        channel: str,
        direction: str,
        purpose: str,
        request_id: Optional[str] = None,
        actor: str = "iam",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.db.add(
            CommunicationAudit(
                channel=channel,
                direction=direction,
                actor=actor,
                purpose=purpose,
                request_id=request_id,
                details=details or {},
            )
        )

    def _request_dict(self, request: CreatorRequest) -> Dict[str, Any]:
        return {
            "request_id": request.request_id,
            "action_type": request.action_type,
            "target_ref": request.target_ref,
            "risk_level": request.risk_level,
            "summary": request.summary,
            "reason": request.reason,
            "consequences": request.consequences or [],
            "status": request.status,
            "requester": request.requester,
            "creator_email": request.creator_email,
            "channel": request.channel,
            "requested_at": _iso(request.requested_at),
            "expires_at": _iso(request.expires_at),
            "resolved_at": _iso(request.resolved_at),
        }

    # ------------------------------------------------------------------ requests

    async def create_request(
        self,
        *,
        action_type: str,
        summary: str,
        consequences: Optional[List[str]] = None,
        risk_level: str = "3",
        target_ref: Optional[str] = None,
        reason: Optional[str] = None,
        requester: str = "iam",
        channel: str = "creator_email",
    ) -> Dict[str, Any]:
        """Create a pending request. Email is only one possible carrier (OD-42 proposed).

        Non-email channels (CLI, webhook, node, air-gapped file) do not require
        CREATOR_EMAIL. Authority is unchanged: only a signed challenge grants it.
        """
        if risk_level not in LEVEL_ORDER:
            raise CreatorApprovalError("risk_level must be 1, 2, 3 or 4")
        allowed_channels = {
            "creator_email", "creator_cli", "creator_webhook",
            "creator_node", "creator_file",
        }
        if channel not in allowed_channels:
            raise CreatorApprovalError(f"unknown Creator channel: {channel}")
        email = settings.creator_email
        if channel == "creator_email" and not email:
            raise CreatorApprovalError(
                "No verified Creator email is configured; use a non-email channel "
                "or set CREATOR_EMAIL"
            )

        request_id = f"cr_{secrets.token_hex(16)}"
        nonce = secrets.token_urlsafe(32)
        expires = _now() + timedelta(seconds=settings.creator_challenge_ttl_seconds)
        payload = {
            "request_id": request_id,
            "action_type": action_type,
            "target_ref": target_ref or "",
            "risk_level": risk_level,
            "summary": summary,
            "consequences": list(consequences or []),
            "nonce": nonce,
            "expires_at": expires.isoformat(),
            "creator_email": email or "",
            "channel": channel,
        }
        payload_hash = hash_payload(payload)

        request = CreatorRequest(
            request_id=request_id,
            action_type=action_type,
            target_ref=target_ref,
            risk_level=risk_level,
            summary=summary,
            reason=reason,
            consequences=list(consequences or []),
            status="pending",
            requester=requester,
            creator_email=email,
            channel=channel,
            expires_at=expires,
            metadata_={"payload_hash": payload_hash},
        )
        self.db.add(request)
        await self.db.flush()
        self.db.add(
            SignedChallenge(
                request_id=request.id,
                nonce=nonce,
                payload=payload,
                payload_hash=payload_hash,
                expires_at=expires,
            )
        )

        body = (
            f"Creator approval request {request_id}\n\n"
            f"Action: {action_type}\n"
            f"Risk level: {risk_level}\n"
            f"Subject: {summary}\n"
            f"Reason: {reason or 'not supplied'}\n"
            f"Target: {target_ref or 'none'}\n"
            f"Channel: {channel}\n"
            "Consequences:\n"
            + "\n".join(f"- {c}" for c in (consequences or []))
            + f"\n\nChallenge hash: {payload_hash}\n"
            f"Nonce: {nonce}\n"
            f"Expires: {expires.isoformat()}\n\n"
            "A plain email reply does NOT authorise anything. Approve or reject only "
            "by returning a signature from the Creator signer over "
            f"'{payload_hash}|approved' or '{payload_hash}|rejected'."
        )
        subject = f"Approval required: {action_type} ({request_id})"
        if channel == "creator_email":
            self.db.add(
                CreatorEmailOutbox(
                    request_id=request_id,
                    recipient=email,
                    subject=subject,
                    body=body,
                    transport=settings.creator_email_transport,
                    status="pending",
                )
            )
        await self._audit(
            channel=channel,
            direction="outbound",
            purpose="creator_approval_request",
            request_id=request_id,
            details={"action_type": action_type, "risk_level": risk_level, "channel": channel},
        )
        await self.db.commit()

        delivery = (
            await self.deliver_request(request_id)
            if channel == "creator_email"
            else {"status": "not_applicable", "channel": channel}
        )
        return {
            "request_id": request_id,
            "to": email,
            "channel": channel,
            "subject": subject,
            "body": body,
            "challenge_hash": payload_hash,
            "expires_at": expires.isoformat(),
            "status": "pending",
            "plain_email_reply_authorises": False,
            "delivery": delivery,
        }

    # ------------------------------------------------------------------ delivery

    async def _outbox(self, request_id: str) -> CreatorEmailOutbox:
        result = await self.db.execute(
            select(CreatorEmailOutbox).where(CreatorEmailOutbox.request_id == request_id)
        )
        outbox = result.scalar_one_or_none()
        if not outbox:
            raise LookupError(f"Email outbox entry not found: {request_id}")
        return outbox

    @staticmethod
    def _outbox_dict(outbox: CreatorEmailOutbox) -> Dict[str, Any]:
        return {
            "request_id": outbox.request_id,
            "recipient": outbox.recipient,
            "subject": outbox.subject,
            "transport": outbox.transport,
            "status": outbox.status,
            "attempts": outbox.attempts,
            "last_error": outbox.last_error,
            "created_at": _iso(outbox.created_at),
            "sent_at": _iso(outbox.sent_at),
        }

    async def deliver_request(
        self, request_id: str, *, force: bool = False
    ) -> Dict[str, Any]:
        """Deliver one queued email. Delivery failure never affects the request."""
        outbox = await self._outbox(request_id)
        if outbox.status == "sent" and not force:
            return {
                "status": "sent",
                "transport": outbox.transport,
                "attempts": outbox.attempts,
                "already_delivered": True,
            }

        message = {
            "request_id": outbox.request_id,
            "to": outbox.recipient,
            "subject": outbox.subject,
            "body": outbox.body,
        }
        try:
            outcome = await transport_from_settings().send(message)
        except Exception as exc:  # delivery must never fail the approval request
            outbox.status = "failed"
            outbox.attempts += 1
            outbox.last_error = str(exc)[:1000]
            await self._audit(
                channel="creator_email",
                direction="outbound",
                purpose="creator_email_failed",
                request_id=request_id,
                details={"transport": outbox.transport, "error": type(exc).__name__},
            )
            dead_lettered = False
            if outbox.attempts >= settings.creator_email_max_attempts:
                await self._dead_letter(outbox, str(exc))
                dead_lettered = True
            await self.db.commit()
            return {
                "status": "failed",
                "transport": outbox.transport,
                "attempts": outbox.attempts,
                "error": str(exc),
                "dead_lettered": dead_lettered,
            }

        outbox.status = outcome["status"]
        outbox.transport = outcome.get("mode", outbox.transport)
        outbox.attempts += 1
        outbox.last_error = None
        outbox.sent_at = _now()
        await self._audit(
            channel="creator_email",
            direction="outbound",
            purpose="creator_email_delivered",
            request_id=request_id,
            details={
                "transport": outbox.transport,
                "delivered_externally": outcome.get("delivered_externally", False),
            },
        )
        await self.db.commit()
        return {
            "status": outbox.status,
            "transport": outbox.transport,
            "attempts": outbox.attempts,
            "delivered_externally": outcome.get("delivered_externally", False),
        }

    async def _dead_letter(self, outbox: CreatorEmailOutbox, error: str) -> None:
        """Stop retrying and alert once a delivery has failed too many times."""
        existing = await self.db.execute(
            select(CreatorEmailDeadLetter).where(
                CreatorEmailDeadLetter.request_id == outbox.request_id
            )
        )
        if not existing.scalar_one_or_none():
            self.db.add(
                CreatorEmailDeadLetter(
                    request_id=outbox.request_id,
                    recipient=outbox.recipient,
                    attempts=outbox.attempts,
                    last_error=error[:1000],
                )
            )
            loguru.logger.error(
                "Creator email dead-lettered: request={} attempts={}",
                outbox.request_id,
                outbox.attempts,
            )
            if settings.creator_alert_webhook_url:
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        await client.post(
                            settings.creator_alert_webhook_url,
                            json={
                                "event": "creator_email_dead_letter",
                                "request_id": outbox.request_id,
                                "attempts": outbox.attempts,
                                "error": error[:500],
                            },
                        )
                except Exception as exc:
                    loguru.logger.warning("Dead-letter alert failed: {}", type(exc).__name__)

    async def retry_failed_deliveries(self) -> List[Dict[str, Any]]:
        """Worker entry point for CM-10 delivery retries, skipping dead letters."""
        dead = await self.db.execute(
            select(CreatorEmailDeadLetter.request_id).where(
                CreatorEmailDeadLetter.resolved_at.is_(None)
            )
        )
        excluded = set(dead.scalars().all())
        result = await self.db.execute(
            select(CreatorEmailOutbox).where(
                CreatorEmailOutbox.status.in_(["pending", "failed"])
            )
        )
        request_ids = [
            row.request_id
            for row in result.scalars().all()
            if row.request_id not in excluded
        ]
        return [await self.deliver_request(rid, force=True) for rid in request_ids]

    async def dead_letters(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(CreatorEmailDeadLetter).order_by(
                CreatorEmailDeadLetter.failed_at.desc()
            )
        )
        return [
            {
                "request_id": row.request_id,
                "recipient": row.recipient,
                "attempts": row.attempts,
                "last_error": row.last_error,
                "failed_at": _iso(row.failed_at),
                "resolved_at": _iso(row.resolved_at),
            }
            for row in result.scalars().all()
        ]

    async def outbox(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(CreatorEmailOutbox).order_by(CreatorEmailOutbox.created_at.desc())
        )
        return [self._outbox_dict(row) for row in result.scalars().all()]

    async def resolve_dead_letter(self, request_id: str) -> Dict[str, Any]:
        """Resolve a dead letter and re-queue its email for immediate retry."""
        result = await self.db.execute(
            select(CreatorEmailDeadLetter).where(
                CreatorEmailDeadLetter.request_id == request_id
            )
        )
        dead = result.scalar_one_or_none()
        if not dead:
            raise LookupError(f"Dead letter not found: {request_id}")
        outbox = await self._outbox(request_id)
        outbox.status = "pending"
        outbox.attempts = 0
        outbox.last_error = None
        dead.resolved_at = _now()
        await self._audit(
            channel="creator_email",
            direction="outbound",
            purpose="creator_email_dead_letter_resolved",
            request_id=request_id,
        )
        await self.db.commit()
        delivery = await self.deliver_request(request_id, force=True)
        return {"request_id": request_id, "resolved": True, "delivery": delivery}

    async def challenge_for_signer(self, request_id: str) -> Dict[str, Any]:
        """Challenge material for the external signer; never includes a private key."""
        request = await self._request(request_id)
        result = await self.db.execute(
            select(SignedChallenge).where(SignedChallenge.request_id == request.id)
        )
        challenge = result.scalar_one_or_none()
        if not challenge:
            raise LookupError(f"Challenge not found for {request_id}")
        digest = challenge.payload_hash
        return {
            "request_id": request_id,
            "challenge_hash": digest,
            "nonce": challenge.nonce,
            "expires_at": _iso(challenge.expires_at),
            "signer_id": settings.creator_signer_id,
            "messages_to_sign": [f"{digest}|approved", f"{digest}|rejected"],
        }

    # ------------------------------------------------------------------ decisions

    async def decide(
        self,
        request_id: str,
        *,
        decision: str,
        signature: str,
        signer_id: str,
    ) -> Dict[str, Any]:
        """Verify a signed challenge. This is the only approval write path."""
        if decision not in {"approved", "rejected"}:
            raise CreatorApprovalError("decision must be 'approved' or 'rejected'")
        request = await self._request(request_id)
        if request.status != "pending":
            raise CreatorApprovalError(f"request is already {request.status}")
        if request.expires_at <= _now():
            request.status = "expired"
            await self.db.commit()
            raise CreatorApprovalError("approval request has expired")

        if signer_id != settings.creator_signer_id:
            raise CreatorApprovalError("signer is not the configured Creator signer")

        result = await self.db.execute(
            select(SignedChallenge).where(SignedChallenge.request_id == request.id)
        )
        challenge = result.scalar_one_or_none()
        if not challenge or challenge.consumed_at or challenge.expires_at <= _now():
            raise CreatorApprovalError("challenge is invalid, consumed or expired")

        try:
            signature_bytes = base64.b64decode(signature, validate=True)
        except Exception as exc:
            raise CreatorApprovalError("signature is not valid base64") from exc
        message = f"{challenge.payload_hash}|{decision}".encode("utf-8")
        try:
            _public_key().verify(signature_bytes, message)
        except InvalidSignature as exc:
            raise CreatorApprovalError("signature verification failed") from exc

        challenge.consumed_at = _now()
        self.db.add(
            CreatorApproval(
                request_id=request.id,
                decision=decision,
                signature=signature,
                signer_id=signer_id,
            )
        )
        request.status = decision
        request.resolved_at = _now()

        authorization = None
        if decision == "approved":
            auth = CreatorAuthorization(
                action_type=request.action_type,
                max_authority_level=request.risk_level,
                target_ref=request.target_ref,
                source_request_id=request.id,
                signer_id=signer_id,
                scope={"request_id": request_id},
                expires_at=_now()
                + timedelta(seconds=settings.creator_authorization_ttl_seconds),
            )
            self.db.add(auth)
            await self.db.flush()
            authorization = str(auth.id)

        await self._audit(
            channel="creator_email",
            direction="inbound",
            purpose=f"creator_{decision}_signed",
            request_id=request_id,
            actor=signer_id,
            details={"challenge_hash": challenge.payload_hash},
        )
        await self.db.commit()
        await self.db.refresh(request)
        response = self._request_dict(request)
        response["signature_verified"] = True
        response["authorization_id"] = authorization
        return response

    # ------------------------------------------------------------------ authority

    async def check_authorization(
        self,
        action_type: str,
        requested_level: str = "3",
        target_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Authoritative check used by Skill Forge and the security engines."""
        requested = LEVEL_ORDER.get(requested_level, 0)
        result = await self.db.execute(
            select(CreatorAuthorization).where(
                CreatorAuthorization.action_type == action_type,
                CreatorAuthorization.is_active == True,  # noqa: E712
            )
        )
        now = _now()
        for auth in result.scalars().all():
            if auth.expires_at <= now or auth.revoked_at:
                continue
            if LEVEL_ORDER.get(auth.max_authority_level, 0) < requested:
                continue
            if auth.target_ref and target_ref and auth.target_ref != target_ref:
                continue
            return {
                "authorized": True,
                "authorization_id": str(auth.id),
                "max_level": auth.max_authority_level,
                "signer_id": auth.signer_id,
                "target_ref": auth.target_ref,
                "expires_at": _iso(auth.expires_at),
            }
        return {
            "authorized": False,
            "reason": (
                "No active signed Creator authorization. Approval must be completed "
                "through the Creator email challenge and hardware signer."
            ),
            "action_type": action_type,
        }

    async def revoke_authorization(self, authorization_id: str) -> bool:
        """Creator-only revocation is invoked by the signed email gateway."""
        result = await self.db.execute(
            select(CreatorAuthorization).where(CreatorAuthorization.id == authorization_id)
        )
        auth = result.scalar_one_or_none()
        if not auth:
            return False
        auth.is_active = False
        auth.revoked_at = _now()
        await self._audit(
            channel="creator_email",
            direction="inbound",
            purpose="creator_authorization_revoked",
            actor=settings.creator_signer_id,
        )
        await self.db.commit()
        return True

    # ------------------------------------------------------------------ queries

    async def list_requests(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        query = select(CreatorRequest)
        if status:
            query = query.where(CreatorRequest.status == status)
        query = query.order_by(CreatorRequest.requested_at.desc())
        result = await self.db.execute(query)
        return [self._request_dict(r) for r in result.scalars().all()]

    async def get_request(self, request_id: str) -> Dict[str, Any]:
        return self._request_dict(await self._request(request_id))

    async def audit(self, request_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = select(CommunicationAudit)
        if request_id:
            query = query.where(CommunicationAudit.request_id == request_id)
        query = query.order_by(CommunicationAudit.created_at.desc())
        result = await self.db.execute(query)
        return [
            {
                "id": str(a.id),
                "channel": a.channel,
                "direction": a.direction,
                "actor": a.actor,
                "purpose": a.purpose,
                "request_id": a.request_id,
                "details": a.details,
                "created_at": _iso(a.created_at),
            }
            for a in result.scalars().all()
        ]
