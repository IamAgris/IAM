"""Disposable security lab and remediation-validation sessions (WH-04/WH-05)."""

from sqlalchemy import Column, Text, JSON, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class SecurityWorkSession(Base):  # type: ignore[misc]
    """A bounded, isolated session bound to a signed scope authorization."""

    __tablename__ = "security_work_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="created")
    target = Column(Text, nullable=False)
    workspace_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workspace_environments.id", ondelete="SET NULL"),
        nullable=True,
    )
    authorization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("creator_authorizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('simulation_lab', 'remediation_validation')",
            name="ck_security_session_kind",
        ),
        CheckConstraint(
            "status IN ('created', 'running', 'verified', 'failed', 'destroyed', 'expired')",
            name="ck_security_session_status",
        ),
    )
