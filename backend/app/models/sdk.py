"""Registered-node and resource-report models (OD-26).

Authentication/scoped credentials are in app.models.auth. Nodes are candidates
until attested; the contribution percentage is a ceiling of operator-permitted
resources, never a claim on total machine capacity.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class RegisteredNode(Base):  # type: ignore[misc]
    """A deployment that offered resources to the core. Candidate, not trusted."""

    __tablename__ = "registered_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    architecture = Column(Text, nullable=False)
    resources = Column(JSON, nullable=False, default=dict)
    capabilities = Column(JSON, nullable=False, default=list)
    trust_level = Column(Text, nullable=False, default="candidate")
    is_active = Column(Boolean, nullable=False, default=False)
    contribution_percent = Column(Float, nullable=False, default=1.0)
    status = Column(Text, nullable=False, default="registered")
    registered_by_token_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "trust_level IN ('candidate', 'restricted', 'trusted', 'revoked')",
            name="ck_registered_node_trust_level",
        ),
        CheckConstraint(
            "contribution_percent >= 0 AND contribution_percent <= 1",
            name="ck_registered_node_contribution_ceiling",
        ),
    )


class NodeResourceReport(Base):  # type: ignore[misc]
    """Bounded, measurable resource report from a node."""

    __tablename__ = "node_resource_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_id = Column(
        UUID(as_uuid=True),
        ForeignKey("registered_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cpu_cores = Column(Integer, nullable=False)
    ram_bytes = Column(Float, nullable=False)
    storage_bytes = Column(Float, nullable=False)
    used_percent = Column(Float, nullable=True)
    contribution_percent = Column(Float, nullable=False)
    permitted_ram_bytes = Column(Float, nullable=False)
    permitted_storage_bytes = Column(Float, nullable=False)
    reported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
