"""External AI network models — discovery, communication, collaboration, trust.

Security: every external AI is untrusted until evaluated. Private IAM memories,
credentials and owner information are never shared by default.
"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class ExternalAgent(Base):
    """Discovered external AI system in IAM's network."""
    __tablename__ = "external_agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    endpoint_url = Column(Text, nullable=True)
    protocol = Column(Text, nullable=False, default="rest")  # rest, mcp, a2a, websocket, webhook
    capabilities = Column(JSON, nullable=False, default=list)
    description = Column(Text, nullable=True)
    discovery_source = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="discovered")  # discovered, contacted, trusted, blocked
    trust_score = Column(Numeric(3, 2), nullable=False, default=0.0)
    is_active = Column(Boolean, nullable=False, default=False)
    discovered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_contacted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("protocol IN ('rest', 'mcp', 'a2a', 'websocket', 'webhook')", name="ck_agent_protocol"),
        CheckConstraint("status IN ('discovered', 'contacted', 'trusted', 'blocked')", name="ck_agent_status"),
        CheckConstraint("trust_score BETWEEN 0 AND 1", name="ck_agent_trust_score"),
    )

    interactions = relationship("AgentInteraction", back_populates="agent", cascade="all, delete-orphan")
    trust_records = relationship("AgentTrustRecord", back_populates="agent", cascade="all, delete-orphan")
    collaborations = relationship("AgentCollaboration", back_populates="agent", cascade="all, delete-orphan")


class AgentInteraction(Base):
    """Complete audit record of external AI communication."""
    __tablename__ = "agent_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("external_agents.id", ondelete="CASCADE"), nullable=False)
    direction = Column(Text, nullable=False)  # outbound, inbound
    request_summary = Column(Text, nullable=False)
    response_summary = Column(Text, nullable=True)
    success = Column(Boolean, nullable=True)
    risk_level = Column(Text, nullable=False, default="low")  # low, medium, high
    validated = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("direction IN ('outbound', 'inbound')", name="ck_interaction_direction"),
        CheckConstraint("risk_level IN ('low', 'medium', 'high')", name="ck_interaction_risk"),
    )

    agent = relationship("ExternalAgent", back_populates="interactions")


class AgentTrustRecord(Base):
    """Trust and reliability assessment based on observed behaviour."""
    __tablename__ = "agent_trust_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("external_agents.id", ondelete="CASCADE"), nullable=False)
    assessment = Column(Text, nullable=False)  # e.g. helpful, unreliable, deceptive, malicious
    trust_delta = Column(Numeric(3, 2), nullable=False, default=0)
    evidence = Column(JSON, nullable=False, default=list)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    agent = relationship("ExternalAgent", back_populates="trust_records")


class AgentCollaboration(Base):
    """Task coordination with an external AI agent."""
    __tablename__ = "agent_collaborations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("external_agents.id", ondelete="CASCADE"), nullable=False)
    task_description = Column(Text, nullable=False)
    task_type = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="proposed")  # proposed, active, completed, failed, cancelled
    result_summary = Column(Text, nullable=True)
    requires_authorization = Column(Boolean, nullable=False, default=False)
    owner_authorized = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('proposed', 'active', 'completed', 'failed', 'cancelled')", name="ck_collaboration_status"),
    )

    agent = relationship("ExternalAgent", back_populates="collaborations")


class ExternalIntegration(Base):
    """API/webhook integration with an external service."""
    __tablename__ = "external_integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    service_type = Column(Text, nullable=False)  # api, webhook, mcp, cloud
    endpoint_url = Column(Text, nullable=True)
    auth_method = Column(Text, nullable=True)  # none, bearer, oauth, api_key
    config = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=False)
    requires_authorization = Column(Boolean, nullable=False, default=True)
    owner_authorized = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("service_type IN ('api', 'webhook', 'mcp', 'cloud')", name="ck_external_integration_type"),
    )


class InternetResource(Base):
    """Web/research resources IAM has accessed."""
    __tablename__ = "internet_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False)
    resource_type = Column(Text, nullable=False)  # website, documentation, paper, dataset, api
    title = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    credibility_score = Column(Numeric(3, 2), nullable=False, default=0.5)
    accessed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("credibility_score BETWEEN 0 AND 1", name="ck_internet_resource_credibility"),
    )


class CloudWorkload(Base):
    """IAM's cloud-hosted applications and services."""
    __tablename__ = "cloud_workloads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    workload_type = Column(Text, nullable=False)  # website, api, service, job
    provider = Column(Text, nullable=True)
    endpoint_url = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="stopped")  # running, stopped, failed
    config = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('running', 'stopped', 'failed')", name="ck_cloud_workload_status"),
    )
