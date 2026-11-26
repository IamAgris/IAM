"""Document 26 (OD-45): HBI persistent memory models.

Records are typed, graded, tiered and auditable. Research material is kept
separate from individual-scope data (OD-05/OD-20).
"""

from sqlalchemy import Column, Text, JSON, Numeric, Integer, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class HBIKnowledgeRecord(Base):
    """A single epistemic object: observation, interpretation, hypothesis or prediction."""

    __tablename__ = "hbi_knowledge_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    record_ref = Column(Text, nullable=False, unique=True, index=True)
    claim = Column(Text, nullable=False)
    epistemic_type = Column(Text, nullable=False)
    evidence_class = Column(Text, nullable=False, default="unverified")
    scope = Column(Text, nullable=False, default="aggregate")
    tier = Column(Text, nullable=False, default="T0")
    population = Column(Text, nullable=True)
    context_dimensions = Column(JSON, nullable=False, default=dict)
    evidence = Column(JSON, nullable=False, default=list)
    confidence = Column(Numeric(3, 2), nullable=False, default=0.0)
    uncertainty = Column(JSON, nullable=False, default=dict)
    alternatives = Column(JSON, nullable=False, default=list)
    falsifier = Column(Text, nullable=True)
    causal_status = Column(Text, nullable=False, default="correlational")
    module_ids = Column(JSON, nullable=False, default=list)
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "epistemic_type IN ('observation','interpretation','hypothesis','prediction')",
            name="ck_hbi_epistemic_type",
        ),
        CheckConstraint(
            "evidence_class IN ('verified','well_supported','contested','unverified','speculation')",
            name="ck_hbi_evidence_class",
        ),
        CheckConstraint("scope IN ('aggregate','individual')", name="ck_hbi_scope"),
        CheckConstraint("tier IN ('T0','T1','T2','T3')", name="ck_hbi_tier"),
        CheckConstraint(
            "causal_status IN ('causal','correlational','speculative')",
            name="ck_hbi_causal_status",
        ),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_hbi_confidence"),
    )


class HBIGraphNode(Base):
    """E1: typed node in the historical/behavioural knowledge graph."""

    __tablename__ = "hbi_graph_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_ref = Column(Text, nullable=False, unique=True, index=True)
    node_type = Column(Text, nullable=False)
    label = Column(Text, nullable=False)
    period = Column(Text, nullable=True)
    region = Column(Text, nullable=True)
    date_low = Column(Numeric(10, 2), nullable=True)
    date_high = Column(Numeric(10, 2), nullable=True)
    properties = Column(JSON, nullable=False, default=dict)
    evidence_class = Column(Text, nullable=False, default="unverified")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "evidence_class IN ('verified','well_supported','contested','unverified','speculation')",
            name="ck_hbi_node_evidence_class",
        ),
    )


class HBIGraphEdge(Base):
    """Typed, evidence-graded relation between two graph nodes."""

    __tablename__ = "hbi_graph_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    edge_ref = Column(Text, nullable=False, unique=True, index=True)
    from_ref = Column(Text, nullable=False, index=True)
    to_ref = Column(Text, nullable=False, index=True)
    relation = Column(Text, nullable=False)
    confidence = Column(Numeric(3, 2), nullable=False, default=0.0)
    evidence_class = Column(Text, nullable=False, default="unverified")
    properties = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_hbi_edge_confidence"),
    )


class HBIDPIASignoff(Base):
    """Durable record of an authorised reviewer's DPIA decision."""

    __tablename__ = "hbi_dpia_signoffs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reviewer = Column(Text, nullable=False)
    decision = Column(Text, nullable=False)
    basis = Column(Text, nullable=False)
    signed_at = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("decision IN ('approved','rejected')", name="ck_hbi_dpia_decision"),
    )


class HBIAuditEvent(Base):
    """Append-only record of governance decisions and HBI operations."""

    __tablename__ = "hbi_audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(Text, nullable=False)
    purpose = Column(Text, nullable=False)
    scope = Column(Text, nullable=False)
    outcome = Column(Text, nullable=False)
    detail = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
