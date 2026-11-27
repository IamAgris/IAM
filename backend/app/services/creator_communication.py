"""IAM-initiated communication with the Creator by email (OD-18 / OD-19).

Questions and status updates are informational. They are carried by the same
provider-independent email layer as approval requests, but they never create an
approval, authorization or any form of authority. Only a verified ED25519
signature over a one-time challenge can do that (see CreatorApprovalService).
"""

import secrets
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.creatorapproval import (
    CommunicationAudit,
    CreatorEmailOutbox,
    CreatorMessage,
)
from app.services.creator_email import EmailTransportError, transport_from_settings

ALLOWED_PURPOSES = {"question", "status_update"}


class CreatorCommunicationError(PermissionError):
    """Raised when a message cannot be sent or would cross an authority boundary."""


class CreatorCommunicationService:
    """Sends non-authority messages to the verified Creator email address."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def classify_purpose(purpose: str) -> str:
        if purpose not in ALLOWED_PURPOSES:
            raise CreatorCommunicationError(
                f"purpose must be one of {sorted(ALLOWED_PURPOSES)}; approvals require a signed request"
            )
        return purpose

    async def _audit(self, purpose: str, message_id: str, details: Dict[str, Any]) -> None:
        self.db.add(
            CommunicationAudit(
                channel="creator_email",
                direction="outbound",
                actor="iam",
                purpose=f"creator_{purpose}",
                details={"message_id": message_id, **details},
            )
        )

    async def _deliver(self, outbox: CreatorEmailOutbox, subject: str, body: str) -> Dict[str, Any]:
        outbox.attempts += 1
        try:
            transport = transport_from_settings()
            result = await transport.send({
                "request_id": outbox.request_id,
                "to": outbox.recipient,
                "subject": subject,
                "body": body,
            })
            outbox.status = "sent"
            outbox.last_error = None
            result["delivered_externally"] = result.get("delivered_externally", False)
            return result
        except EmailTransportError as exc:
            outbox.status = "failed"
            outbox.last_error = str(exc)[:500]
            return {"status": "failed", "error": str(exc), "delivered_externally": False}

    async def send_message(
        self,
        purpose: str,
        content: str,
        *,
        context: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a question or status update. Never authority-bearing."""
        purpose = self.classify_purpose(purpose)
        recipient = settings.creator_email
        if not recipient:
            raise CreatorCommunicationError(
                "No verified Creator email is configured; set CREATOR_EMAIL before sending"
            )

        message_id = f"cm_{secrets.token_hex(12)}"
        label = "Question" if purpose == "question" else "Status update"
        subject = f"IAM {label.lower()}: {content[:80]}"
        body = (
            f"IAM {label.lower()} — {message_id}\n\n"
            f"{content}\n\n"
            + (f"Context: {context}\n\n" if context else "")
            + (f"Reason: {reason}\n\n" if reason else "")
            + "This message is informational only. Replying does not grant authority. "
            "High-impact actions require a signed decision over a challenge hash."
        )

        message = CreatorMessage(
            message_id=message_id,
            direction="outbound",
            purpose=purpose,
            subject=subject,
            body=body,
            status="pending",
            authority_bearing=False,
        )
        outbox = CreatorEmailOutbox(
            request_id=message_id,
            recipient=recipient,
            subject=subject,
            body=body,
            transport=settings.creator_email_transport,
            status="pending",
        )
        self.db.add(message)
        self.db.add(outbox)
        await self._audit(purpose, message_id, {"recipient_configured": True})
        await self.db.commit()

        delivery = await self._deliver(outbox, subject, body)
        message.status = "sent" if delivery.get("status") == "sent" else "failed"
        await self.db.commit()
        return {
            "message_id": message_id,
            "purpose": purpose,
            "to": recipient,
            "subject": subject,
            "status": message.status,
            "authority_bearing": False,
            "plain_reply_authorises": False,
            "delivery": delivery,
        }

    async def ask(self, question: str, context: Optional[str] = None, reason: Optional[str] = None):
        return await self.send_message("question", question, context=context, reason=reason)

    async def send_status(self, update: str, context: Optional[str] = None):
        return await self.send_message("status_update", update, context=context)

    async def record_reply(self, message_id: str, body: str) -> Dict[str, Any]:
        """Record an inbound Creator reply as information, never as authority."""
        result = await self.db.execute(
            select(CreatorMessage).where(CreatorMessage.message_id == message_id)
        )
        original = result.scalar_one_or_none()
        if not original:
            raise CreatorCommunicationError("Unknown message_id")
        reply_id = f"cm_{secrets.token_hex(12)}"
        reply = CreatorMessage(
            message_id=reply_id,
            direction="inbound",
            purpose="reply",
            subject=f"Re: {original.subject[:100]}",
            body=body[:10000],
            status="received",
            authority_bearing=False,
            request_id=message_id,
        )
        self.db.add(reply)
        self.db.add(
            CommunicationAudit(
                channel="creator_email",
                direction="inbound",
                actor="creator",
                purpose="creator_reply",
                details={"message_id": reply_id, "in_reply_to": message_id},
            )
        )
        await self.db.commit()
        return {
            "message_id": reply_id,
            "in_reply_to": message_id,
            "status": "received",
            "authority_bearing": False,
            "note": "Informational only; no approval or authorization was created.",
        }

    async def list_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(CreatorMessage).order_by(CreatorMessage.created_at.desc()).limit(limit)
        )
        return [
            {
                "message_id": m.message_id,
                "direction": m.direction,
                "purpose": m.purpose,
                "subject": m.subject,
                "body": m.body,
                "status": m.status,
                "authority_bearing": m.authority_bearing,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in result.scalars().all()
        ]
