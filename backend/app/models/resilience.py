"""Resilience engine SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class HealthCheck(Base):  # type: ignore[misc]
    """Service health monitoring records."""
    __tablename__ = "health_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(Text, nullable=False)
    status = Column(Text, nullable=False)  # healthy, degraded, down
    response_time_ms = Column(Integer, nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('healthy', 'degraded', 'down')", name="ck_health_check_status"),
    )


class RecoveryLog(Base):  # type: ignore[misc]
    """Automatic recovery actions taken."""
    __tablename__ = "recovery_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    success = Column(Boolean, nullable=False)
    details = Column(JSON, nullable=False, default=dict)
    performed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class BackupVerification(Base):  # type: ignore[misc]
    """Backup restoration verification records."""
    __tablename__ = "backup_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backup_id = Column(Text, nullable=False)
    verification_type = Column(Text, nullable=False)  # full, partial, integrity
    success = Column(Boolean, nullable=False)
    restored_items = Column(Integer, nullable=True)
    verified_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IncidentRecord(Base):  # type: ignore[misc]
    """Security and failure incident records."""
    __tablename__ = "incident_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_type = Column(Text, nullable=False)  # security, failure, outage, suspicious_activity
    severity = Column(Text, nullable=False)  # low, medium, high, critical
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name="ck_incident_severity"),
    )


class CredentialRotation(Base):  # type: ignore[misc]
    """Credential rotation history."""
    __tablename__ = "credential_rotations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    integration_id = Column(UUID(as_uuid=True), ForeignKey("integration_registry.id", ondelete="SET NULL"), nullable=True)
    secret_name = Column(Text, nullable=False)
    rotated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    next_rotation_due = Column(DateTime(timezone=True), nullable=True)
