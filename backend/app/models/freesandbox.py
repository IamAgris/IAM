"""Persistence for OEDIE free infrastructure provider adapters (Doc 22).

Providers are always candidate infrastructure. Quota readings, environments
and collected results are recorded so a restart does not lose lifecycle state.
No credential value is stored here — only the name of the secret source.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


def _now():
    return datetime.now(timezone.utc)


class FreeSandboxProvider(Base):
    __tablename__ = "free_sandbox_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(Text, nullable=False, unique=True)
    provider_type = Column(Text, nullable=False)
    capabilities = Column(JSON, nullable=False, default=list)
    terms_url = Column(Text, nullable=False, default="")
    docs_verified_at = Column(DateTime(timezone=True), nullable=True)
    headless = Column(Boolean, nullable=False, default=True)
    registration_status = Column(
        Text,
        nullable=False,
        default="candidate",
    )
    is_active = Column(Boolean, nullable=False, default=False)
    credential_env = Column(Text, nullable=True)  # env-var NAME only, never a secret
    config = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "registration_status IN "
            "('candidate', 'registered', 'pending_creator_approval', 'unavailable')",
            name="ck_free_sandbox_registration_status",
        ),
    )


class FreeSandboxQuotaSnapshot(Base):
    __tablename__ = "free_sandbox_quota_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("free_sandbox_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    used_percent = Column(Numeric(5, 2), nullable=True)
    remaining = Column(Numeric, nullable=True)
    unit = Column(Text, nullable=False, default="")
    resets_at = Column(DateTime(timezone=True), nullable=True)
    source_url = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    captured_at = Column(DateTime(timezone=True), default=_now, nullable=False)


class FreeSandboxEnvironment(Base):
    __tablename__ = "free_sandbox_environments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("free_sandbox_providers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_id = Column(Text, nullable=False)
    task_id = Column(Text, nullable=False, index=True)
    capability = Column(Text, nullable=False)
    state = Column(Text, nullable=False, default="provisioning")
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "state IN ('discovered','registered','provisioning','running',"
            "'stopped','completed','failed','deleted')",
            name="ck_free_sandbox_environment_state",
        ),
    )


class FreeSandboxResult(Base):
    __tablename__ = "free_sandbox_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    environment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("free_sandbox_environments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payload = Column(JSON, nullable=False, default=dict)
    artifacts = Column(JSON, nullable=False, default=list)
    error = Column(Text, nullable=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
