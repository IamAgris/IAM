"""Model independence SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class ModelComparison(Base):  # type: ignore[misc]
    """Testing and comparing new foundation models."""
    __tablename__ = "model_comparisons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name = Column(Text, nullable=False)
    provider = Column(Text, nullable=False)
    model_id = Column(Text, nullable=False)
    capabilities_tested = Column(JSON, nullable=False, default=list)
    scores = Column(JSON, nullable=False, default=dict)
    overall_score = Column(Numeric(5, 4), nullable=True)
    tested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_adopted = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint("overall_score BETWEEN 0 AND 1", name="ck_model_comparison_score"),
    )


class ModelPortabilityExport(Base):  # type: ignore[misc]
    """Export memory and identity in provider-independent format."""
    __tablename__ = "model_portability_exports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    export_format = Column(Text, nullable=False)  # json, markdown, yaml
    export_scope = Column(JSON, nullable=False, default=list)  # identity, memory, goals, skills
    exported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    export_location = Column(Text, nullable=True)


class FallbackConfig(Base):  # type: ignore[misc]
    """Fallback model configuration if primary provider unavailable."""
    __tablename__ = "fallback_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    primary_model = Column(Text, nullable=False)
    fallback_model = Column(Text, nullable=False)
    fallback_provider = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
