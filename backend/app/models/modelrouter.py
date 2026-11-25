"""Model provider catalog and intelligence router models.

NVIDIA is one provider among many. IAM's identity, memory and autonomy are
independent of any single provider.
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AIProvider(Base):
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


class DiscoveredModel(Base):
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


class RoutingDecision(Base):
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


class ProviderUsage(Base):
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
