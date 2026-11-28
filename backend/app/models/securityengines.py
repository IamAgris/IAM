"""External Security Engine registry, scopes, tasks and findings.

ARTEX is an optional, replaceable engine in this subsystem. It is never part of
IAM's protected core and cannot authorise its own operations. Everything that
leaves IAM passes through the IAM Security Guard.
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


class ExternalSecurityEngine(Base):  # type: ignore[misc]
    """A configured external security-testing engine (e.g. ARTEX)."""

    __tablename__ = "security_engines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    provider = Column(Text, nullable=False, default="artex")
    transport = Column(Text, nullable=False, default="mcp_streamable_http")
    base_url = Column(Text, nullable=False)
    token_env_var = Column(Text, nullable=False, default="ARTEX_MCP_TOKEN")

    enabled = Column(Boolean, nullable=False, default=False)
    dry_run = Column(Boolean, nullable=False, default=True)
    allow_private_network = Column(Boolean, nullable=False, default=False)
    allow_execution = Column(Boolean, nullable=False, default=False)
    allowed_scopes = Column(JSON, nullable=False, default=list)  # e.g. ["read"]

    created_by = Column(Text, nullable=False, default="owner")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "provider IN ('artex', 'generic')", name="ck_security_engine_provider"
        ),
        CheckConstraint(
            "transport IN ('mcp_streamable_http', 'http_api', 'stub')",
            name="ck_security_engine_transport",
        ),
    )


class SecurityEngineScope(Base):  # type: ignore[misc]
    """Explicit, owner-registered target allowlist entry."""

    __tablename__ = "security_engine_scopes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_id = Column(
        UUID(as_uuid=True),
        ForeignKey("security_engines.id", ondelete="CASCADE"),
        nullable=False,
    )
    target = Column(Text, nullable=False)
    target_type = Column(Text, nullable=False, default="host")  # host | cidr | lab_url
    description = Column(Text, nullable=True)
    authorization_id = Column(Text, nullable=True)
    authorized_by = Column(Text, nullable=False, default="owner")
    allow_write = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SecurityEngineTask(Base):  # type: ignore[misc]
    """One IAM-controlled security-testing task sent to an external engine."""

    __tablename__ = "security_engine_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_id = Column(
        UUID(as_uuid=True),
        ForeignKey("security_engines.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_id = Column(
        UUID(as_uuid=True),
        ForeignKey("security_engine_scopes.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("security_engine_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    target = Column(Text, nullable=False)
    operation = Column(Text, nullable=False, default="read")
    description = Column(Text, nullable=False)
    risk_level = Column(Text, nullable=False, default="sensitive")
    status = Column(Text, nullable=False, default="pending_approval")

    created_by = Column(Text, nullable=False, default="iam")
    approved_by = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    external_task_id = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_approval', 'authorized', 'dispatched', 'running', "
            "'completed', 'failed', 'cancelled', 'rejected')",
            name="ck_security_task_status",
        ),
        CheckConstraint(
            "risk_level IN ('personal', 'operational', 'sensitive', 'protected_core')",
            name="ck_security_task_risk",
        ),
    )


class SecurityFinding(Base):  # type: ignore[misc]
    """Normalised, untrusted finding evidence returned by an external engine."""

    __tablename__ = "security_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("security_engine_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    severity = Column(Text, nullable=False, default="informational")
    description = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=False, default=list)
    raw = Column(JSON, nullable=False, default=dict)
    remediation = Column(Text, nullable=True)
    verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SecurityEngineAudit(Base):  # type: ignore[misc]
    """Append-only record of every engine configuration and task action."""

    __tablename__ = "security_engine_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    engine_id = Column(
        UUID(as_uuid=True),
        ForeignKey("security_engines.id", ondelete="SET NULL"),
        nullable=True,
    )
    task_id = Column(
        UUID(as_uuid=True),
        ForeignKey("security_engine_tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    action = Column(Text, nullable=False)
    actor = Column(Text, nullable=False, default="iam")
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
