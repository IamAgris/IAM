"""AI Assistant Interoperability and Technology Learning Lab (OD-28).

Internal research capability, not a visitor feature. Study public technology,
integrate only through official interfaces, then reproduce capabilities
independently. No vendor identity, private model or private system is copied.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class AssistantSystem(Base):
    __tablename__ = "assistant_systems"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    vendor = Column(Text, nullable=False)
    official_docs_url = Column(Text, nullable=False)
    integration_method = Column(Text, nullable=False, default="official_interface_only")
    public_capabilities = Column(JSON, nullable=False, default=list)
    terms_url = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="studied")
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('studied', 'integration_available', 'replicated')",
            name="ck_assistant_system_status",
        ),
    )


class AssistantResearchNote(Base):
    __tablename__ = "assistant_research_notes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assistant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assistant_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic = Column(Text, nullable=False)
    observation = Column(Text, nullable=False)
    source_url = Column(Text, nullable=False)
    source_date = Column(DateTime(timezone=True), nullable=True)
    confidence = Column(Float, nullable=False, default=0.5)
    status = Column(Text, nullable=False, default="observation")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('observation', 'verified', 'uncertain')",
            name="ck_assistant_note_status",
        ),
    )


class AssistantAdapter(Base):
    __tablename__ = "assistant_adapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assistant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assistant_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(Text, nullable=False)
    interface_type = Column(Text, nullable=False)
    endpoint_template = Column(Text, nullable=True)
    auth_method = Column(Text, nullable=False, default="operator_provided_credential")
    requires_credential = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "interface_type IN ('official_skill', 'app_intents', 'shortcuts', "
            "'automation_studio', 'official_api', 'documentation_only')",
            name="ck_assistant_adapter_interface",
        ),
    )


class ReplicationExperiment(Base):
    __tablename__ = "replication_experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capability = Column(Text, nullable=False)
    hypothesis = Column(Text, nullable=False)
    method = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False, default=dict)
    result = Column(Text, nullable=False, default="planned")
    isolated = Column(Boolean, nullable=False, default=True)
    production_adopted = Column(Boolean, nullable=False, default=False)
    creator_approval_reference = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "result IN ('planned', 'running', 'succeeded', 'failed')",
            name="ck_replication_experiment_result",
        ),
    )


class CapabilityComparison(Base):
    __tablename__ = "capability_comparisons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assistant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assistant_systems.id", ondelete="CASCADE"),
        nullable=False,
    )
    capability = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)
    evidence_note = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("rating BETWEEN 0 AND 5", name="ck_capability_comparison_rating"),
    )
