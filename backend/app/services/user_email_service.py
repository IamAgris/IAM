"""Opt-in email carrier for private user communication (OD-59 / Doc 39).

The existing per-visitor conversation store remains the single message system:
email messages are written to a dedicated thread through ``GlobalAccessService``.
Email is only a transport. A verified address is not an authority and never
grants access to another visitor's data.
"""

import asyncio
import hashlib
import hmac
import os
import re
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any, Dict, Optional

import loguru
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.creatorapproval import CommunicationAudit
from app.models.user_email import UserEmailInbound, UserEmailOptIn, UserEmailOutbox
from app.services.crypto_service import CryptoService
from app.services.globalaccess_service import GlobalAccessService

logger = loguru.logger
crypto = CryptoService()

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class UserEmailError(RuntimeError):
    """Opt-in, delivery or inbound verification failed. Never carries secrets."""


def _as_uuid(value: Any) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise UserEmailError("invalid visitor identifier") from exc


def _email_hash(address: str) -> str:
    return hashlib.sha256(address.strip().lower().encode("utf-8")).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class UserEmailService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------ helpers

    async def _opt_in_row(self, visitor_id: Any) -> Optional[UserEmailOptIn]:
        result = await self.db.execute(
            select(UserEmailOptIn).where(UserEmailOptIn.visitor_id == _as_uuid(visitor_id))
        )
        return result.scalar_one_or_none()

    def _require_enabled(self) -> None:
        if not settings.user_email_enabled:
            raise UserEmailError("user email channel is disabled")

    def _normalise_address(self, address: str) -> str:
        value = (address or "").strip().lower()
        if not EMAIL_RE.fullmatch(value):
            raise UserEmailError("a valid email address is required")
        domain = settings.user_email_domain.strip().lower()
        actual = value.rsplit("@", 1)[1]
        if domain and actual != domain and not actual.endswith("." + domain):
            raise UserEmailError("email address is outside the permitted domain")
        return value

    def _clean_body(self, content: str) -> str:
        value = (content or "").strip()
        if not value:
            raise UserEmailError("message body is empty")
        limit = max(1, settings.user_email_max_body_chars)
        return value[:limit]

    def _audit(self, direction: str, purpose: str, visitor_id: Any, **details: Any) -> None:
        self.db.add(
            CommunicationAudit(
                channel="private_user",
                direction=direction,
                actor="iam" if direction == "outbound" else "user",
                purpose=purpose,
                details={"transport": "email", "visitor_id": str(visitor_id), **details},
            )
        )

    @staticmethod
    def _send_blocking(recipient: str, subject: str, body: str) -> None:
        host = settings.user_email_smtp_host
        sender = settings.user_email_from
        if not host or not sender:
            raise UserEmailError("USER_EMAIL_SMTP_HOST and USER_EMAIL_FROM must be configured")
        password = os.environ.get(settings.user_email_smtp_password_env, "")
        message = EmailMessage()
        message["From"] = sender
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(host, settings.user_email_smtp_port, timeout=20) as client:
            if settings.user_email_smtp_use_tls:
                client.starttls()
            if settings.user_email_smtp_user:
                if not password:
                    raise UserEmailError(
                        f"SMTP password missing from {settings.user_email_smtp_password_env}"
                    )
                client.login(settings.user_email_smtp_user, password)
            client.send_message(message)

    async def _deliver(self, recipient: str, subject: str, body: str) -> None:
        self._require_enabled()
        try:
            await asyncio.to_thread(self._send_blocking, recipient, subject, body)
        except UserEmailError:
            raise
        except Exception as exc:
            raise UserEmailError(f"delivery failed: {type(exc).__name__}") from exc

    # ------------------------------------------------------------------- public

    async def status(self, visitor_id: Any) -> Dict[str, Any]:
        row = await self._opt_in_row(visitor_id)
        return {
            "enabled": settings.user_email_enabled,
            "status": row.status if row else "not_opted_in",
            "verified_at": row.verified_at.isoformat() if row and row.verified_at else None,
        }

    async def opt_in(self, visitor_id: Any, email: str) -> Dict[str, Any]:
        """Start opt-in. A single-use token is emailed to the supplied address."""
        self._require_enabled()
        address = self._normalise_address(email)
        uid = _as_uuid(visitor_id)
        address_hash = _email_hash(address)

        conflict = await self.db.execute(
            select(UserEmailOptIn).where(UserEmailOptIn.email_hash == address_hash)
        )
        other = conflict.scalar_one_or_none()
        if other is not None and _as_uuid(other.visitor_id) != uid:
            raise UserEmailError("email address is already bound to another visitor")

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=max(60, settings.user_email_verification_ttl_seconds)
        )
        row = await self._opt_in_row(uid)
        if row is None:
            row = UserEmailOptIn(visitor_id=uid)
            self.db.add(row)
        row.email_ciphertext = crypto.encrypt(address)  # type: ignore[assignment]
        row.email_hash = address_hash  # type: ignore[assignment]
        row.status = "pending"  # type: ignore[assignment]
        row.verification_token_hash = _token_hash(token)  # type: ignore[assignment]
        row.verification_expires_at = expires_at  # type: ignore[assignment]
        row.opted_out_at = None  # type: ignore[assignment]
        row.verified_at = None  # type: ignore[assignment]
        row.email_session_token = None  # type: ignore[assignment]
        row.email_thread_id = None  # type: ignore[assignment]
        await self.db.commit()

        body = (
            "IAM received a request to use this address for private chat by email.\n\n"
            f"Verification token: {token}\n\n"
            "Return this token to IAM in the app. A token is single-use and expires "
            "shortly. If you did not request this, ignore the message.\n\n"
            "Never send passwords, banking details or identity documents by email."
        )
        await self._deliver(address, "Confirm your IAM email chat", body)
        return {"status": "pending", "address": self._mask(address)}

    async def verify(self, visitor_id: Any, token: str) -> Dict[str, Any]:
        """Bind the address only after the one-time token matches."""
        self._require_enabled()
        row = await self._opt_in_row(visitor_id)
        if row is None or row.status != "pending":
            raise UserEmailError("no pending opt-in for this visitor")
        if not row.verification_expires_at or row.verification_expires_at < datetime.now(timezone.utc):
            raise UserEmailError("verification token has expired")
        if not hmac.compare_digest(str(row.verification_token_hash or ""), _token_hash(token or "")):
            raise UserEmailError("invalid verification token")

        session = await GlobalAccessService(self.db).create_session(
            str(row.visitor_id), mode="focus", resolve_geo=False
        )
        row.status = "verified"  # type: ignore[assignment]
        row.verified_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        row.verification_token_hash = None  # type: ignore[assignment]
        row.verification_expires_at = None  # type: ignore[assignment]
        row.email_session_token = session["session_token"]
        row.email_thread_id = uuid.UUID(str(session["default_thread_id"]))  # type: ignore[assignment]
        await self.db.commit()
        self._audit("inbound", "user_email_opt_in_verified", row.visitor_id)
        await self.db.commit()
        return {"status": "verified", "verified_at": row.verified_at.isoformat()}

    async def opt_out(self, visitor_id: Any) -> Dict[str, Any]:
        """Stop outbound email and revoke the address binding."""
        row = await self._opt_in_row(visitor_id)
        if row is None:
            return {"status": "not_opted_in"}
        row.status = "revoked"  # type: ignore[assignment]
        row.opted_out_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        row.verification_token_hash = None  # type: ignore[assignment]
        row.verification_expires_at = None  # type: ignore[assignment]
        row.email_session_token = None  # type: ignore[assignment]
        await self.db.commit()
        self._audit("outbound", "user_email_opt_out", row.visitor_id)
        await self.db.commit()
        return {"status": "revoked"}

    async def send_message(self, visitor_id: Any, content: str) -> Dict[str, Any]:
        """Send one IAM reply to the verified address and record it in the thread."""
        self._require_enabled()
        row = await self._opt_in_row(visitor_id)
        if row is None or row.status != "verified":
            raise UserEmailError("a verified opt-in is required before sending email")
        if not row.email_session_token or not row.email_thread_id:
            raise UserEmailError("email conversation thread is not available")
        body = self._clean_body(content)
        recipient = crypto.decrypt(str(row.email_ciphertext))

        await GlobalAccessService(self.db).add_message(
            str(row.email_session_token), "assistant", body, str(row.email_thread_id), mode="email"
        )
        outbox = UserEmailOutbox(
            visitor_id=row.visitor_id,
            recipient_ciphertext=crypto.encrypt(recipient),
            subject="IAM",
            body_ciphertext=crypto.encrypt(body),
            transport="smtp",
            status="pending",
        )
        self.db.add(outbox)
        await self.db.flush()
        try:
            await self._deliver(recipient, str(outbox.subject), body)
            outbox.status = "sent"  # type: ignore[assignment]
            outbox.sent_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        except UserEmailError as exc:
            outbox.status = "failed"  # type: ignore[assignment]
            outbox.last_error = str(exc)[:200]  # type: ignore[assignment]
        outbox.attempts = 1  # type: ignore[assignment]
        await self.db.commit()
        self._audit("outbound", "user_email_reply", row.visitor_id)
        await self.db.commit()
        return {"status": outbox.status}

    async def receive(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Accept an HMAC-verified forward from a verified, opted-in user."""
        self._require_enabled()
        provider_id = str(payload.get("message_id") or "").strip()
        if not provider_id:
            raise UserEmailError("provider message id is required")
        body = self._clean_body(str(payload.get("body") or ""))
        address = self._normalise_address(str(payload.get("email") or ""))
        subject = str(payload.get("subject") or "")[:200]

        duplicate = await self.db.execute(
            select(UserEmailInbound).where(UserEmailInbound.provider_message_id == provider_id)
        )
        if duplicate.scalar_one_or_none() is not None:
            return {"status": "duplicate"}

        result = await self.db.execute(
            select(UserEmailOptIn).where(
                UserEmailOptIn.email_hash == _email_hash(address),
                UserEmailOptIn.status == "verified",
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            # Unverified or unknown sender: never enters a user conversation.
            raise UserEmailError("no verified opt-in for this sender")
        if not row.email_session_token or not row.email_thread_id:
            raise UserEmailError("email conversation thread is not available")

        inbound = UserEmailInbound(
            provider_message_id=provider_id,
            visitor_id=row.visitor_id,
            thread_id=row.email_thread_id,
        )
        self.db.add(inbound)
        await self.db.flush()
        await GlobalAccessService(self.db).add_message(
            str(row.email_session_token),
            "user",
            body,
            str(row.email_thread_id),
            mode="email",
        )
        await self.db.commit()
        self._audit("inbound", "user_email_message", row.visitor_id, subject=subject)
        await self.db.commit()
        return {"status": "accepted"}

    async def retry_failed(self, limit: int = 25) -> Dict[str, int]:
        """Retry failed outbound messages; dead-letter after the configured limit."""
        self._require_enabled()
        result = await self.db.execute(
            select(UserEmailOutbox)
            .where(UserEmailOutbox.status == "failed")
            .limit(max(1, min(limit, 100)))
        )
        rows = result.scalars().all()
        sent = failed = dead = 0
        for row in rows:
            row.attempts = int(row.attempts) + 1  # type: ignore[assignment]
            if row.attempts >= settings.user_email_max_attempts:
                row.status = "dead_letter"  # type: ignore[assignment]
                dead += 1
                continue
            recipient = crypto.decrypt(str(row.recipient_ciphertext))
            body = crypto.decrypt(str(row.body_ciphertext))
            try:
                await self._deliver(recipient, str(row.subject), body)
                row.status = "sent"  # type: ignore[assignment]
                row.sent_at = datetime.now(timezone.utc)  # type: ignore[assignment]
                sent += 1
            except UserEmailError as exc:
                row.last_error = str(exc)[:200]  # type: ignore[assignment]
                failed += 1
        await self.db.commit()
        return {"sent": sent, "failed": failed, "dead_letter": dead}

    @staticmethod
    def _mask(address: str) -> str:
        local, _, domain = address.partition("@")
        head = local[:2] if local else ""
        return f"{head}***@{domain}"
