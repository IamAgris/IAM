"""Capability registry SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class CapabilityDefinition(Base):  # type: ignore[misc]
    """Catalogue of what IAM can do, cannot do, wants to learn."""
    __tablename__ = "capability_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    category = Column(Text, nullable=False)  # programming, languages, mathematics, business, science, communication, cybersecurity, finance, robotics
    description = Column(Text, nullable=True)
    target_proficiency = Column(Integer, nullable=False, default=100)
    is_learnable = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("category IN ('programming', 'languages', 'mathematics', 'business', 'science', 'communication', 'cybersecurity', 'finance', 'robotics')", name="ck_capability_category"),
        CheckConstraint("target_proficiency BETWEEN 0 AND 100", name="ck_capability_target_proficiency"),
    )

    assessments = relationship("CapabilityAssessment", back_populates="capability", cascade="all, delete-orphan")


class CapabilityAssessment(Base):  # type: ignore[misc]
    """Measurable assessment of a capability."""
    __tablename__ = "capability_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capability_id = Column(UUID(as_uuid=True), ForeignKey("capability_definitions.id", ondelete="CASCADE"), nullable=False)
    proficiency_level = Column(Integer, nullable=False, default=0)
    assessment_method = Column(Text, nullable=False)  # test, project, simulation, review
    evidence = Column(JSON, nullable=False, default=list)
    assessed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assessor = Column(Text, nullable=True)  # 'self', 'external', 'automated'

    __table_args__ = (
        CheckConstraint("proficiency_level BETWEEN 0 AND 100", name="ck_capability_assessment_level"),
        CheckConstraint("assessment_method IN ('test', 'project', 'simulation', 'review')", name="ck_capability_assessment_method"),
    )

    capability = relationship("CapabilityDefinition", back_populates="assessments")


class LearningPath(Base):  # type: ignore[misc]
    """Planned learning journey for a capability."""
    __tablename__ = "learning_paths"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capability_id = Column(UUID(as_uuid=True), ForeignKey("capability_definitions.id", ondelete="CASCADE"), nullable=False)
    current_step = Column(Integer, nullable=False, default=0)
    total_steps = Column(Integer, nullable=False, default=0)
    steps = Column(JSON, nullable=False, default=list)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
