"""Model provider catalog and intelligence router models.

NVIDIA is one provider among many. IAM's identity, memory and autonomy are
independent of any single provider.
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AIProvider(Base):  # type: ignore[misc]
    """A model provider (NVIDIA, Alibaba, OpenAI, Ollama, etc.)."""
    __tablename__ = "ai_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    provider_type = Column(Text, nullable=False)  # hosted, local, nvidia, openweight
    base_url = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    free_only = Column(Boolean, nullable=False, default=False)
    config = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("provider_type IN ('hosted', 'local', 'nvidia', 'openweight')", name="ck_ai_provider_type"),
    )


class DiscoveredModel(Base):  # type: ignore[misc]
    """A model discovered from a provider catalogue (not hardcoded)."""
    __tablename__ = "discovered_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), nullable=False)
    model_id = Column(Text, nullable=False)  # provider's model identifier
    display_name = Column(Text, nullable=True)
    capabilities = Column(JSON, nullable=False, default=list)  # reasoning, coding, vision, embeddings
    context_length = Column(Integer, nullable=True)
    is_free = Column(Boolean, nullable=False, default=False)
    is_available = Column(Boolean, nullable=False, default=True)
    cost_input_per_1m = Column(Numeric(12, 6), nullable=True)
    cost_output_per_1m = Column(Numeric(12, 6), nullable=True)
    quality_score = Column(Numeric(5, 4), nullable=True)
    discovered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)

    # OD-52 Phase A: live catalogue registry fields. Never assume a catalogue
    # entry is an available endpoint or supports a capability.
    model_type = Column(Text, nullable=False, default="llm")
    access_type = Column(Text, nullable=False, default="free")
    endpoint_status = Column(Text, nullable=False, default="unknown")
    alias = Column(Text, nullable=True)  # LiteLLM model_name used for execution
    input_capabilities = Column(JSON, nullable=False, default=list)
    output_capabilities = Column(JSON, nullable=False, default=list)
    tool_calling = Column(Boolean, nullable=False, default=False)
    reasoning = Column(Boolean, nullable=False, default=False)
    structured_output = Column(Boolean, nullable=False, default=False)
    api_protocol = Column(Text, nullable=False, default="chat_completions")
    last_tested = Column(DateTime(timezone=True), nullable=True)
    test_result = Column(JSON, nullable=True)
    restrictions = Column(JSON, nullable=False, default=dict)
    metadata_source = Column(Text, nullable=True)
    last_known_good = Column(JSON, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "model_type IN ('llm', 'embedding', 'vision', 'speech', 'image')",
            name="ck_discovered_model_type",
        ),
        CheckConstraint(
            "access_type IN ('free', 'paid', 'local')",
            name="ck_discovered_model_access",
        ),
        CheckConstraint(
            "endpoint_status IN ('available', 'unavailable', 'unknown')",
            name="ck_discovered_model_endpoint_status",
        ),
        CheckConstraint(
            "api_protocol IN ('chat_completions', 'responses', 'embeddings', 'other')",
            name="ck_discovered_model_protocol",
        ),
    )


class RoutingDecision(Base):  # type: ignore[misc]
    """Audit of which model was selected for a task and why."""
    __tablename__ = "routing_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_type = Column(Text, nullable=False)
    required_capabilities = Column(JSON, nullable=False, default=list)
    selected_provider = Column(Text, nullable=False)
    selected_model = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    fallback_used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ProviderUsage(Base):  # type: ignore[misc]
    """Usage and remaining limits tracking to avoid unexpected charges."""
    __tablename__ = "provider_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), nullable=False)
    model_id = Column(Text, nullable=True)
    tokens_input = Column(Integer, nullable=False, default=0)
    tokens_output = Column(Integer, nullable=False, default=0)
    estimated_cost_usd = Column(Numeric(12, 6), nullable=False, default=0)
    period = Column(Text, nullable=False)  # e.g. 2026-11
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
