"""Security and external integrations module SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class IntegrationRegistry(Base):
    __tablename__ = "integration_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    provider = Column(Text, nullable=False)
    integration_type = Column(Text, nullable=False)
    config = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    requires_creator_approval = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    permissions = relationship("IntegrationPermission", back_populates="integration", cascade="all, delete-orphan")
    credentials = relationship("CredentialReference", back_populates="integration", cascade="all, delete-orphan")


class IntegrationPermission(Base):
    __tablename__ = "integration_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integration_registry.id", ondelete="CASCADE"), nullable=False)
    permission_scope = Column(Text, nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    integration = relationship("IntegrationRegistry", back_populates="permissions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(Text, nullable=False)
    actor = Column(Text, nullable=False)
    target = Column(Text, nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SecurityIncident(Base):
    __tablename__ = "security_incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(Text, nullable=False, default="medium")
    status = Column(Text, nullable=False, default="open")
    reported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="ck_incident_severity"),
        CheckConstraint("status IN ('open', 'investigating', 'resolved', 'closed')", name="ck_incident_status"),
    )


class CredentialReference(Base):
    __tablename__ = "credential_references"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integration_registry.id", ondelete="CASCADE"), nullable=False)
    secret_name = Column(Text, nullable=False)
    secret_store = Column(Text, nullable=False)
    secret_path = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    integration = relationship("IntegrationRegistry", back_populates="credentials")
