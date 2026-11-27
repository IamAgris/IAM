"""Doc 20 / OD-36: Technology Capability Registry.

Tracks external SDKs, frameworks, models and runtimes that IAM has researched.
This is distinct from the capability registry for IAM's own abilities and from
the MEFE model registry: it records third-party technologies and their licence,
cost, architecture support and lifecycle state before any adoption.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class TechnologyCapability(Base):
    """One discovered third-party technology with evidence and lifecycle state."""

    __tablename__ = "technology_capabilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, index=True)
    version = Column(Text, nullable=True)
    official_source = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    architectures = Column(JSON, nullable=False, default=list)
    licence = Column(Text, nullable=True)
    commercial_use_ok = Column(Boolean, nullable=False, default=False)
    cost_status = Column(Text, nullable=False, default="free")
    hardware_requirements = Column(JSON, nullable=False, default=dict)
    capabilities = Column(JSON, nullable=False, default=list)
    limitations = Column(JSON, nullable=False, default=list)
    security_status = Column(Text, nullable=True)
    maintenance_status = Column(Text, nullable=True)
    compatibility = Column(JSON, nullable=False, default=dict)
    test_results = Column(JSON, nullable=False, default=list)
    benchmarks = Column(JSON, nullable=False, default=list)
    lifecycle_state = Column(Text, nullable=False, default="researched", index=True)
    notes = Column(Text, nullable=True)
    discovered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "cost_status IN ('free', 'open_source', 'paid', 'mixed')",
            name="ck_tech_cost_status",
        ),
        CheckConstraint(
            "lifecycle_state IN ('researched', 'tested', 'approved', 'integrated', 'deprecated', 'rejected')",
            name="ck_tech_lifecycle_state",
        ),
    )
