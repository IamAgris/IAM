"""Doc 19 / OD-35: free infrastructure node candidates and lifecycle.

Distinct from Doc 22 free-sandbox providers (notebooks/spaces) and from the OD-26
registered-node table. A candidate here is an assessed possibility; it becomes a
node only through the authorised node protocol and creator approval.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Integer, JSON, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class FreeNodeCandidate(Base):  # type: ignore[misc]
    """A discovered free compute resource assessed for supplementary use."""

    __tablename__ = "free_node_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(Text, nullable=False, index=True)
    instance_class = Column(Text, nullable=True)
    architecture = Column(Text, nullable=False)  # amd64 | arm64
    region = Column(Text, nullable=True)
    cpu_cores = Column(Numeric(4, 2), nullable=False, default=0)
    ram_mb = Column(Integer, nullable=False, default=0)
    disk_gb = Column(Numeric(6, 2), nullable=False, default=0)
    cost_status = Column(Text, nullable=False, default="free")
    terms_source = Column(Text, nullable=True)
    eligibility_verified = Column(Boolean, nullable=False, default=False)
    useful = Column(Boolean, nullable=False, default=False)
    usefulness_reason = Column(Text, nullable=True)
    run_compatible = Column(Boolean, nullable=False, default=False)
    status = Column(Text, nullable=False, default="discovered", index=True)
    authorisation_required = Column(Boolean, nullable=False, default=True)
    registered_node_id = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    quota_alarm_at = Column(DateTime(timezone=True), nullable=True)
    migration_plan = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    discovered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("architecture IN ('amd64', 'arm64')", name="ck_freenode_arch"),
        CheckConstraint(
            "cost_status IN ('free', 'free_credit', 'unknown')", name="ck_freenode_cost_status"
        ),
        CheckConstraint(
            "status IN ('discovered', 'assessed', 'authorised', 'deployed', 'registered', "
            "'expiring', 'migrated', 'stopped', 'rejected')",
            name="ck_freenode_status",
        ),
    )
