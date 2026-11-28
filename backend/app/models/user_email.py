"""Opt-in email carrier for private user communication (OD-59 / Doc 39).

Email is a transport for the existing per-visitor conversation store, not a
second message system. Addresses and message bodies are field-encrypted with the
existing AES-GCM service; only a one-way hash of the normalised address is used
for lookup. An email address is never an identity proof until verified.
"""

import uuid

from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class UserEmailOptIn(Base):  # type: ignore[misc]
    """One opt-in per visitor. Email address is encrypted at rest."""

    __tablename__ = "user_email_opt_ins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("anonymous_visitors.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    email_ciphertext = Column(Text, nullable=False)
    email_hash = Column(Text, nullable=False, unique=True, index=True)
    status = Column(Text, nullable=False, default="pending")
    verification_token_hash = Column(Text, nullable=True)
    verification_expires_at = Column(DateTime(timezone=True), nullable=True)
    email_session_token = Column(Text, nullable=True)
    email_thread_id = Column(UUID(as_uuid=True), nullable=True)
    opted_in_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    opted_out_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'verified', 'revoked')",
            name="ck_user_email_opt_in_status",
        ),
    )


class UserEmailOutbox(Base):  # type: ignore[misc]
    """Delivery state for outbound user email; body is encrypted at rest."""

    __tablename__ = "user_email_outbox"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("anonymous_visitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_ciphertext = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    body_ciphertext = Column(Text, nullable=False)
    transport = Column(Text, nullable=False, default="smtp")
    status = Column(Text, nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'dead_letter')",
            name="ck_user_email_outbox_status",
        ),
    )


class UserEmailInbound(Base):  # type: ignore[misc]
    """Provider message ids, deduplicated so a replayed forward cannot duplicate chat."""

    __tablename__ = "user_email_inbound"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_message_id = Column(Text, nullable=False, unique=True, index=True)
    visitor_id = Column(
        UUID(as_uuid=True),
        ForeignKey("anonymous_visitors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    thread_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
