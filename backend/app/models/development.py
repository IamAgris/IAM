"""Self-development module SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class ModelRegistry(Base):  # type: ignore[misc]
    __tablename__ = "model_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    provider = Column(Text, nullable=False)
    model_id = Column(Text, nullable=False)
    capabilities = Column(JSON, nullable=False, default=list)
    cost_per_token_input = Column(Numeric(10, 6), nullable=True)
    cost_per_token_output = Column(Numeric(10, 6), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    versions = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")
    evaluations = relationship("ModelEvaluation", back_populates="model", cascade="all, delete-orphan")


class ModelVersion(Base):  # type: ignore[misc]
    __tablename__ = "model_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.id", ondelete="CASCADE"), nullable=False)
    version = Column(Text, nullable=False)
    is_primary = Column(Boolean, nullable=False, default=False)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    model = relationship("ModelRegistry", back_populates="versions")


class ModelEvaluation(Base):  # type: ignore[misc]
    __tablename__ = "model_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("model_registry.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(Text, nullable=True)
    score = Column(Numeric(5, 4), nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    model = relationship("ModelRegistry", back_populates="evaluations")


class Experiment(Base):  # type: ignore[misc]
    __tablename__ = "experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    hypothesis = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    results = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'running', 'completed', 'failed')", name="ck_experiment_status"),
    )


class SoftwareProject(Base):  # type: ignore[misc]
    __tablename__ = "software_projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="planning")
    repository_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('planning', 'in_development', 'testing', 'deployed', 'archived')", name="ck_software_project_status"),
    )

    code_changes = relationship("CodeChange", back_populates="project", cascade="all, delete-orphan")
    deployments = relationship("DeploymentRecord", back_populates="project", cascade="all, delete-orphan")


class CodeChange(Base):  # type: ignore[misc]
    __tablename__ = "code_changes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("software_projects.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    change_type = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="proposed")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("change_type IN ('add', 'modify', 'delete')", name="ck_code_change_type"),
        CheckConstraint("status IN ('proposed', 'reviewed', 'tested', 'deployed', 'rejected')", name="ck_code_change_status"),
    )

    project = relationship("SoftwareProject", back_populates="code_changes")


class DeploymentRecord(Base):  # type: ignore[misc]
    __tablename__ = "deployment_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("software_projects.id", ondelete="CASCADE"), nullable=False)
    version = Column(Text, nullable=True)
    environment = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="pending")
    deployed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'success', 'failed', 'rolled_back')", name="ck_deployment_status"),
    )

    project = relationship("SoftwareProject", back_populates="deployments")


class ResourceMetric(Base):  # type: ignore[misc]
    __tablename__ = "resource_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_name = Column(Text, nullable=False)
    value = Column(Numeric(15, 4), nullable=False)
    unit = Column(Text, nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UpgradeHistory(Base):  # type: ignore[misc]
    __tablename__ = "upgrade_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component = Column(Text, nullable=False)
    previous_version = Column(Text, nullable=True)
    new_version = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'completed', 'rolled_back')", name="ck_upgrade_status"),
    )
