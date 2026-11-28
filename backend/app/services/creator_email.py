"""Provider-independent delivery for Creator approval emails.

Transport selection is configuration, not code. The default ``log`` transport
records the package in the outbox and sends nothing, so a fresh deployment is
safe. SMTP and HTTP transports require explicit credentials from the environment;
no credential is ever stored in the database or API response.
"""

import asyncio
import os
import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from typing import Any, Dict

import httpx
import loguru

from app.core.config import settings

logger = loguru.logger


class EmailTransportError(RuntimeError):
    """Delivery failed; the approval request itself is unaffected."""


class CreatorEmailTransport(ABC):
    name = "abstract"

    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        ...


class LogTransport(CreatorEmailTransport):
    """Records the package without sending anything (safe default)."""

    name = "log"

    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(
            "Creator email package recorded (not sent): request={} to={} subject={}",
            message.get("request_id"),
            message.get("to"),
            message.get("subject"),
        )
        return {"status": "sent", "mode": "log", "delivered_externally": False}


class SmtpTransport(CreatorEmailTransport):
    """Standard SMTP with STARTTLS, credentials read from the environment."""

    name = "smtp"

    def __init__(self):
        self.host = settings.creator_smtp_host
        self.port = settings.creator_smtp_port
        self.user = settings.creator_smtp_user
        self.sender = settings.creator_email_from or self.user
        self.password = os.environ.get(settings.creator_smtp_password_env, "")
        self.use_tls = settings.creator_smtp_use_tls
        if not self.host or not self.sender:
            raise EmailTransportError("SMTP host and creator_email_from must be configured")

    @staticmethod
    def _assert_creator_domain(recipient: str) -> None:
        """Refuse to send approval mail outside the configured Creator domain."""
        domain = (settings.creator_email_domain or "").strip().lower().lstrip("@")
        if not domain:
            return
        configured = (settings.creator_email or "").strip().lower()
        address = recipient.strip().lower()
        if not address.endswith(f"@{domain}"):
            raise EmailTransportError("recipient is outside the Creator email domain")
        if configured and configured != address:
            raise EmailTransportError("recipient does not match the verified Creator email")

    def _send_blocking(self, message: Dict[str, Any]) -> None:
        recipient = str(message.get("to") or "")
        self._assert_creator_domain(recipient)
        email = EmailMessage()
        email["From"] = self.sender
        email["To"] = str(message.get("to") or "")
        email["Subject"] = str(message.get("subject") or "")
        email.set_content(str(message.get("body") or ""))
        with smtplib.SMTP(self.host, self.port, timeout=20) as client:
            if self.use_tls:
                client.starttls()
            if self.user:
                if not self.password:
                    raise EmailTransportError(
                        f"SMTP password missing from {settings.creator_smtp_password_env}"
                    )
                client.login(self.user, self.password)
            client.send_message(email)

    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        try:
            await asyncio.to_thread(self._send_blocking, message)
        except EmailTransportError:
            raise
        except Exception as exc:
            raise EmailTransportError(f"SMTP delivery failed: {type(exc).__name__}") from exc
        return {"status": "sent", "mode": "smtp", "delivered_externally": True}


class HttpTransport(CreatorEmailTransport):
    """POST the package to an operator-controlled email gateway."""

    name = "http"

    def __init__(self):
        self.url = settings.creator_email_http_url
        self.token = os.environ.get(settings.creator_email_http_token_env, "")
        if not self.url:
            raise EmailTransportError("creator_email_http_url must be configured")

    async def send(self, message: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
                response = await client.post(self.url, json=message, headers=headers)
        except httpx.HTTPError as exc:
            raise EmailTransportError(f"HTTP delivery failed: {type(exc).__name__}") from exc
        if response.status_code < 200 or response.status_code >= 300:
            raise EmailTransportError(f"HTTP delivery rejected ({response.status_code})")
        return {"status": "sent", "mode": "http", "delivered_externally": True}


def transport_from_settings() -> CreatorEmailTransport:
    name = (settings.creator_email_transport or "log").lower()
    if name == "log":
        return LogTransport()
    if name == "smtp":
        return SmtpTransport()
    if name == "http":
        return HttpTransport()
    raise EmailTransportError(f"unknown Creator email transport: {name}")
