"""AI Communication & Collaboration models (Module C).

Tracks AI identity registry, capability discovery, conversation threads,
context exchange, response verification, AI reputation records,
communication permissions, human communication bridge, and audit trail.
"""

from typing import Optional
from datetime import datetime
from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AIIdentityRegistry(Base):  # type: ignore[misc]
    """AI systems IAM knows about and can communicate with."""

    __tablename__ = "ai_identity_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    provider = Column(Text, nullable=False)
    model_id = Column(Text, nullable=True)
    communication_channel = Column(Text, nullable=False)  # browser, local_api, human_mediated, email, other
    is_local = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    communication_permitted = Column(Boolean, nullable=False, default=False)
    trust_level = Column(Text, nullable=False, default="untrusted")  # untrusted, trusted, restricted
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("trust_level IN ('untrusted', 'trusted', 'restricted')",
                        name="ck_ai_identity_trust_level"),
    )


class AICapabilityRegistry(Base):  # type: ignore[misc]
    """What each AI system can do, with confidence scores."""

    __tablename__ = "ai_capability_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_identity_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    capability = Column(Text, nullable=False)  # reasoning, coding, research, analysis, creative_writing, code_review, architecture_review
    confidence_score = Column(Integer, nullable=False, default=50)  # 0-100
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    evidence = Column(JSON, nullable=False, default=list)

    __table_args__ = (
        CheckConstraint("confidence_score BETWEEN 0 AND 100",
                        name="ck_ai_capability_confidence_score"),
    )


class AIConversationThread(Base):  # type: ignore[misc]
    """Conversation threads per AI system."""

    __tablename__ = "ai_conversation_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_identity_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(Text, nullable=False)
    topic = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="active")  # active, paused, completed, archived
    is_human_mediated = Column(Boolean, nullable=False, default=False)
    message_count = Column(Integer, nullable=False, default=0)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'completed', 'archived')",
                        name="ck_ai_conversation_status"),
    )


class AIConversationMessage(Base):  # type: ignore[misc]
    """Individual messages within a conversation thread."""

    __tablename__ = "ai_conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversation_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender = Column(Text, nullable=False)  # iam, ai, human
    content = Column(Text, nullable=False)
    message_type = Column(Text, nullable=False, default="text")  # text, question, answer, code, system
    confidence_score = Column(Integer, nullable=True)  # 0-100
    verification_status = Column(Text, nullable=False, default="unverified")  # unverified, verified, disputed, false
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("sender IN ('iam', 'ai', 'human')",
                        name="ck_ai_message_sender"),
        CheckConstraint("confidence_score IS NULL OR confidence_score BETWEEN 0 AND 100",
                        name="ck_ai_message_confidence"),
        CheckConstraint("verification_status IN ('unverified', 'verified', 'disputed', 'false')",
                        name="ck_ai_message_verification"),
    )


class AIContextExchange(Base):  # type: ignore[misc]
    """Context shared with an AI system."""

    __tablename__ = "ai_context_exchange"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_identity_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversation_threads.id", ondelete="SET NULL"),
        nullable=True,
    )
    context_type = Column(Text, nullable=False)  # project, task, research, architecture, code
    content = Column(JSON, nullable=False, default=dict)
    is_shared = Column(Boolean, nullable=False, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AIResponseVerification(Base):  # type: ignore[misc]
    """Verification of AI responses."""

    __tablename__ = "ai_response_verification"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    message_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversation_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_claim = Column(Text, nullable=False)
    verified_claim = Column(Text, nullable=True)
    verification_method = Column(Text, nullable=False)  # independent_reasoning, external_source, code_execution, human_review
    confidence = Column(Integer, nullable=False, default=50)  # 0-100
    evidence_references = Column(JSON, nullable=False, default=list)
    verified_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    verified_by = Column(Text, nullable=False, default="iam")  # iam, external, human

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 100",
                        name="ck_ai_response_verification_confidence"),
        CheckConstraint("verification_method IN ('independent_reasoning', 'external_source', 'code_execution', 'human_review')",
                        name="ck_ai_response_verification_method"),
    )


class AIReputationRecord(Base):  # type: ignore[misc]
    """Per-AI reliability tracking."""

    __tablename__ = "ai_reputation_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_identity_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    accuracy_score = Column(Integer, nullable=False, default=50)  # 0-100
    honesty_score = Column(Integer, nullable=False, default=50)  # 0-100
    helpfulness_score = Column(Integer, nullable=False, default=50)  # 0-100
    total_interactions = Column(Integer, nullable=False, default=0)
    correct_predictions = Column(Integer, nullable=False, default=0)
    incorrect_predictions = Column(Integer, nullable=False, default=0)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("accuracy_score BETWEEN 0 AND 100",
                        name="ck_ai_reputation_accuracy_score"),
        CheckConstraint("honesty_score BETWEEN 0 AND 100",
                        name="ck_ai_reputation_honesty_score"),
        CheckConstraint("helpfulness_score BETWEEN 0 AND 100",
                        name="ck_ai_reputation_helpfulness_score"),
    )


class AICommunicationPermission(Base):  # type: ignore[misc]
    """Per-AI permission rules."""

    __tablename__ = "ai_communication_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_identity_registry.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    can_share_project_context = Column(Boolean, nullable=False, default=False)
    can_share_research_findings = Column(Boolean, nullable=False, default=False)
    can_share_code = Column(Boolean, nullable=False, default=False)
    can_receive_private_data = Column(Boolean, nullable=False, default=False)
    can_initiate_contact = Column(Boolean, nullable=False, default=False)
    can_receive_responses = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class HumanCommunicationBridge(Base):  # type: ignore[misc]
    """Human-mediated communication: IAM prepares, human submits, human returns response."""

    __tablename__ = "human_communication_bridge"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_identity_registry.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_conversation_threads.id", ondelete="SET NULL"),
        nullable=True,
    )
    iam_message = Column(Text, nullable=False)
    human_response = Column(Text, nullable=True)
    ai_response = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")  # pending, awaiting_human, completed, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'awaiting_human', 'completed', 'cancelled')",
                        name="ck_human_communication_status"),
    )


class AICommunicationAudit(Base):  # type: ignore[misc]
    """Audit trail for all AI communication events."""

    __tablename__ = "ai_communication_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ai_identity_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_identity_registry.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    actor = Column(Text, nullable=False)  # iam, ai, human
    action = Column(Text, nullable=False)
    event_type = Column(Text, nullable=False)  # send, receive, verify, approve, revoke, escalate
    target = Column(Text, nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
