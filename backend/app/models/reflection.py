"""Reflection engine SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class ReflectionEntry(Base):  # type: ignore[misc]
    """Review decisions and experiences."""
    __tablename__ = "reflection_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reflection_type = Column(Text, nullable=False)  # decision, experience, outcome, principle
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    lesson_learned = Column(Text, nullable=True)
    confidence = Column(Numeric(3, 2), nullable=False, default=0.5)
    related_decision_ids = Column(JSON, nullable=False, default=list)
    related_memory_ids = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_reflection_confidence"),
    )


class OperatingPrinciple(Base):  # type: ignore[misc]
    """IAM's evolving operating principles."""
    __tablename__ = "operating_principles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    principle_name = Column(Text, nullable=False)
    principle_statement = Column(Text, nullable=False)
    category = Column(Text, nullable=False)  # safety, legal, security, operational, personal
    is_mutable = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("category IN ('safety', 'legal', 'security', 'operational', 'personal')", name="ck_operating_principle_category"),
    )
