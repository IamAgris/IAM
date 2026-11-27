"""IAM Skill Forge persistence models.

This is a *separate* subsystem from the legacy ``skills`` capability/proficiency
registry in ``app.models.memory``. Those tables record what IAM has learned;
these tables track versioned, permission-scoped skill packages that IAM's
Skill Runtime loads and executes.

Trust rules encoded here:
- every package has a version history and an audit trail;
- privileged packages cannot become active without explicit creator approval;
- protected-core packages can never be authored by IAM itself.
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


class SkillPackage(Base):
    """Registry entry for one skill (native or imported), with its current version."""

    __tablename__ = "skillforge_packages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(Text, nullable=False, unique=True, index=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    origin = Column(Text, nullable=False, default="native")  # native | imported
    provider = Column(Text, nullable=True)  # openai | nvidia | google | anthropic | community
    category = Column(Text, nullable=True)
    classification = Column(Text, nullable=False)  # personal | operational | sensitive | protected_core
    status = Column(Text, nullable=False, default="draft")

    version = Column(Text, nullable=False, default="1.0.0")
    manifest = Column(JSON, nullable=False, default=dict)
    permissions = Column(JSON, nullable=False, default=list)
    network_access = Column(Boolean, nullable=False, default=False)
    filesystem_access = Column(Text, nullable=False, default="none")
    requires_creator_approval = Column(Boolean, nullable=False, default=False)

    path = Column(Text, nullable=True)  # relative to skillforge_root
    checksum = Column(Text, nullable=True)  # sha256 of all skill files

    created_by = Column(Text, nullable=False, default="iam")
    approved_by = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "origin IN ('native', 'imported')",
            name="ck_skillforge_origin",
        ),
        CheckConstraint(
            "classification IN ('personal', 'operational', 'sensitive', 'protected_core')",
            name="ck_skillforge_classification",
        ),
        CheckConstraint(
            "status IN ('draft', 'testing', 'pending_approval', 'published', "
            "'active', 'quarantined', 'archived')",
            name="ck_skillforge_status",
        ),
        CheckConstraint(
            "filesystem_access IN ('none', 'scoped', 'full')",
            name="ck_skillforge_filesystem_access",
        ),
        CheckConstraint(
            "provider IS NULL OR provider IN "
            "('openai', 'nvidia', 'google', 'anthropic', 'microsoft', 'community')",
            name="ck_skillforge_provider",
        ),
    )


class SkillVersion(Base):
    """Immutable snapshot of a skill manifest at a given version."""

    __tablename__ = "skillforge_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skillforge_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(Text, nullable=False)
    manifest = Column(JSON, nullable=False, default=dict)
    permissions = Column(JSON, nullable=False, default=list)
    checksum = Column(Text, nullable=True)
    change_note = Column(Text, nullable=True)
    is_current = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("version ~ '^[0-9]+\\.[0-9]+\\.[0-9]+$'", name="ck_skillforge_version_semver"),
    )


class SkillTestResult(Base):
    """Evidence produced by the Skill Testing Engine for one version."""

    __tablename__ = "skillforge_test_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skillforge_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(Text, nullable=False)
    test_type = Column(Text, nullable=False)  # manifest | security | functional
    passed = Column(Boolean, nullable=False)
    details = Column(JSON, nullable=False, default=list)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SkillAuditEvent(Base):
    """Append-only audit trail for every Skill Forge state change."""

    __tablename__ = "skillforge_audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skillforge_packages.id", ondelete="CASCADE"),
        nullable=True,
    )
    action = Column(Text, nullable=False)
    actor = Column(Text, nullable=False, default="iam")
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SkillPermissionGrant(Base):
    """Owner-issued, skill-scoped permission grants.

    A skill manifest is descriptive only. Grants live here, outside the skill
    package, so a skill can never widen its own authority by editing its files.
    """

    __tablename__ = "skillforge_permission_grants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skillforge_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    permission = Column(Text, nullable=False)
    granted_by = Column(Text, nullable=False, default="owner")
    reason = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
