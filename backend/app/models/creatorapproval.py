"""Creator approval by email with signed challenges (OD-18 / OD-19).

There is no Creator UI. Email carries the request and its explanation; authority
comes only from a verified signature over a one-time challenge. A plain email
reply can never create an approval or authorization.
"""

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class CreatorRequest(Base):
    """A request sent to the verified Creator email address for a decision."""

    __tablename__ = "creator_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Text, nullable=False, unique=True, index=True)
    action_type = Column(Text, nullable=False, index=True)
    target_ref = Column(Text, nullable=True)
    risk_level = Column(Text, nullable=False, default="3")
    summary = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    consequences = Column(JSON, nullable=False, default=list)
    status = Column(Text, nullable=False, default="pending")

    requester = Column(Text, nullable=False, default="iam")
    creator_email = Column(Text, nullable=True)
    channel = Column(Text, nullable=False, default="creator_email")

    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('1', '2', '3', '4')", name="ck_creator_request_risk"
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled')",
            name="ck_creator_request_status",
        ),
    )


class SignedChallenge(Base):
    """One-time challenge whose hash is signed by the Creator's external signer."""

    __tablename__ = "signed_challenges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("creator_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    nonce = Column(Text, nullable=False, unique=True)
    payload = Column(JSON, nullable=False, default=dict)
    payload_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)


class CreatorApproval(Base):
    """Verified decision. Created only after signature verification succeeds."""

    __tablename__ = "creator_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("creator_requests.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision = Column(Text, nullable=False)
    signature = Column(Text, nullable=False)
    signer_id = Column(Text, nullable=False)
    verified_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'rejected')", name="ck_creator_approval_decision"
        ),
    )


class CreatorAuthorization(Base):
    """Scoped authorization created from a verified signed approval.

    IAM has no write path to this table except through CreatorApprovalService,
    which requires a valid signature. There is no 'owner UI' flag.
    """

    __tablename__ = "creator_authorizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action_type = Column(Text, nullable=False, index=True)
    max_authority_level = Column(Text, nullable=False, default="3")
    target_ref = Column(Text, nullable=True)
    source_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("creator_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    signer_id = Column(Text, nullable=False)
    scope = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "max_authority_level IN ('1', '2', '3', '4')",
            name="ck_creator_auth_level",
        ),
    )


class CreatorMessage(Base):
    """IAM-initiated non-authority communication with the Creator (OD-18/OD-19).

    Questions and status updates travel by email. They are informational: a plain
    reply can never create an approval or authorization. The database constraint
    makes that separation permanent.
    """
    __tablename__ = "creator_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(Text, nullable=False, unique=True, index=True)
    direction = Column(Text, nullable=False)  # outbound, inbound
    purpose = Column(Text, nullable=False)  # question, status_update, reply
    subject = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="pending")
    authority_bearing = Column(Boolean, nullable=False, default=False)
    request_id = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("direction IN ('outbound', 'inbound')", name="ck_creator_message_direction"),
        CheckConstraint("purpose IN ('question', 'status_update', 'reply')", name="ck_creator_message_purpose"),
        CheckConstraint("authority_bearing = false", name="ck_creator_message_no_authority"),
    )


class CreatorEmailOutbox(Base):
    """Queued Creator approval email, with delivery state for retries."""

    __tablename__ = "creator_email_outbox"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Text, nullable=False, unique=True, index=True)
    recipient = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    transport = Column(Text, nullable=False, default="log")
    status = Column(Text, nullable=False, default="pending")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'sent', 'failed', 'skipped')",
            name="ck_creator_outbox_status",
        ),
    )


class CreatorEmailDeadLetter(Base):
    """A Creator approval email that could not be delivered after retries."""

    __tablename__ = "creator_email_dead_letters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(Text, nullable=False, unique=True, index=True)
    recipient = Column(Text, nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    failed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class CommunicationAudit(Base):
    """Audit for all three channels; creator approvals are never off the record."""

    __tablename__ = "communication_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel = Column(Text, nullable=False)  # creator_email | operational_email | private_user
    direction = Column(Text, nullable=False)  # outbound | inbound
    actor = Column(Text, nullable=False, default="iam")
    purpose = Column(Text, nullable=False)
    request_id = Column(Text, nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "channel IN ('creator_email', 'operational_email', 'private_user')",
            name="ck_communication_channel",
        ),
        CheckConstraint(
            "direction IN ('outbound', 'inbound')", name="ck_communication_direction"
        ),
    )
