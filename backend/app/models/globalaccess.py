"""Global access & multi-user intelligence layer models

One central IAM identity, many isolated anonymous visitor sessions.
GeoIP is context only — never an identity. Session tokens distinguish visitors.
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AnonymousVisitor(Base):  # type: ignore[misc]
    """Pseudonymous visitor identity — not a person, not tied to IP permanently."""
    __tablename__ = "anonymous_visitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_token = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    account_id = Column(UUID(as_uuid=True), nullable=True)  # Optional registered account link

    sessions = relationship("VisitorSession", back_populates="visitor", cascade="all, delete-orphan")


class VisitorSession(Base):  # type: ignore[misc]
    """An isolated conversation session for one visitor."""
    __tablename__ = "visitor_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_id = Column(UUID(as_uuid=True), ForeignKey("anonymous_visitors.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(64), nullable=False, unique=True, index=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    mode = Column(String(16), nullable=False, default="focus")  # focus, recall, create
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint("mode IN ('focus', 'recall', 'create')", name="ck_session_mode"),
    )

    visitor = relationship("AnonymousVisitor", back_populates="sessions")
    location = relationship("VisitorLocation", back_populates="session", uselist=False, cascade="all, delete-orphan")
    threads = relationship("ConversationThread", back_populates="session", cascade="all, delete-orphan")


class VisitorLocation(Base):  # type: ignore[misc]
    """Coarse GeoIP context — an estimate, never a verified identity."""
    __tablename__ = "visitor_locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("visitor_sessions.id", ondelete="CASCADE"), nullable=False)
    country = Column(Text, nullable=True)
    region = Column(Text, nullable=True)
    city = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    timezone = Column(Text, nullable=True)
    currency = Column(Text, nullable=True)
    is_estimate = Column(Boolean, nullable=False, default=True)
    user_corrected = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("VisitorSession", back_populates="location")


class ConversationThread(Base):  # type: ignore[misc]
    """Separate conversation per visitor session — private context."""
    __tablename__ = "conversation_threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("visitor_sessions.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    session = relationship("VisitorSession", back_populates="threads")
    messages = relationship("VisitorMessage", back_populates="thread", cascade="all, delete-orphan")


class VisitorMessage(Base):  # type: ignore[misc]
    """Individual message within a visitor's private conversation."""
    __tablename__ = "visitor_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("conversation_threads.id", ondelete="CASCADE"), nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    mode = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="ck_visitor_message_role"),
    )

    thread = relationship("ConversationThread", back_populates="messages")


class VisitorPreference(Base):  # type: ignore[misc]
    """Permitted remembered preferences for anonymous visitors."""
    __tablename__ = "visitor_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_id = Column(UUID(as_uuid=True), ForeignKey("anonymous_visitors.id", ondelete="CASCADE"), nullable=False)
    key = Column(Text, nullable=False)
    value = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class VisitorConsent(Base):  # type: ignore[misc]
    """Privacy and data-retention choices."""
    __tablename__ = "visitor_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_id = Column(UUID(as_uuid=True), ForeignKey("anonymous_visitors.id", ondelete="CASCADE"), nullable=False)
    consent_type = Column(Text, nullable=False)  # anonymous_memory, analytics, retention_days
    granted = Column(Boolean, nullable=False, default=False)
    retention_days = Column(Integer, nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class VisitorMemoryPermission(Base):  # type: ignore[misc]
    """Controls whether visitor data may enter any memory layer."""
    __tablename__ = "visitor_memory_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_id = Column(UUID(as_uuid=True), ForeignKey("anonymous_visitors.id", ondelete="CASCADE"), nullable=False)
    allow_session_memory = Column(Boolean, nullable=False, default=True)
    allow_anonymous_memory = Column(Boolean, nullable=False, default=True)  # OD-05
    allow_shared_knowledge = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class RequestJob(Base):  # type: ignore[misc]
    """Queued and executing visitor requests."""
    __tablename__ = "request_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("visitor_sessions.id", ondelete="SET NULL"), nullable=True)
    status = Column(Text, nullable=False, default="queued")  # queued, running, completed, failed
    mode = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')", name="ck_request_job_status"),
    )


class RequestUsage(Base):  # type: ignore[misc]
    """Resource and usage accounting per visitor/session."""
    __tablename__ = "request_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), nullable=True)
    tokens_input = Column(Integer, nullable=False, default=0)
    tokens_output = Column(Integer, nullable=False, default=0)
    provider = Column(Text, nullable=True)
    model = Column(Text, nullable=True)
    cost_usd = Column(Numeric(12, 6), nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class VisitorRateLimit(Base):  # type: ignore[misc]
    """Abuse and usage controls per visitor or IP-derived key."""
    __tablename__ = "visitor_rate_limits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visitor_id = Column(UUID(as_uuid=True), nullable=True)
    scope_key = Column(Text, nullable=False)  # visitor token or IP hash
    window_start = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    request_count = Column(Integer, nullable=False, default=0)
    is_blocked = Column(Boolean, nullable=False, default=False)


class RegionalSetting(Base):  # type: ignore[misc]
    """Regional language, currency and time-zone defaults."""
    __tablename__ = "regional_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    country_code = Column(Text, nullable=False, unique=True)
    language = Column(Text, nullable=True)
    currency = Column(Text, nullable=True)
    timezone = Column(Text, nullable=True)
    defaults = Column(JSON, nullable=False, default=dict)
