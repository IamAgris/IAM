"""Research lab SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class ResearchHypothesis(Base):  # type: ignore[misc]
    """Research questions and hypotheses."""
    __tablename__ = "research_hypotheses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    hypothesis_statement = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="proposed")  # proposed, testing, confirmed, refuted, inconclusive
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    tested_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('proposed', 'testing', 'confirmed', 'refuted', 'inconclusive')", name="ck_hypothesis_status"),
    )

    experiments = relationship("ResearchExperiment", back_populates="hypothesis", cascade="all, delete-orphan")


class ResearchExperiment(Base):  # type: ignore[misc]
    """Experiments and simulations."""
    __tablename__ = "research_experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hypothesis_id = Column(UUID(as_uuid=True), ForeignKey("research_hypotheses.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    methodology = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="planned")  # planned, running, completed, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('planned', 'running', 'completed', 'failed')", name="ck_experiment_status"),
    )

    hypothesis = relationship("ResearchHypothesis", back_populates="experiments")
    results = relationship("ExperimentResult", back_populates="experiment", cascade="all, delete-orphan")


class ExperimentResult(Base):  # type: ignore[misc]
    """Recorded experiment results including failures."""
    __tablename__ = "experiment_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_id = Column(UUID(as_uuid=True), ForeignKey("research_experiments.id", ondelete="CASCADE"), nullable=False)
    outcome = Column(Text, nullable=False)
    success = Column(Boolean, nullable=False)
    data = Column(JSON, nullable=False, default=dict)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reproducible = Column(Boolean, nullable=False, default=False)

    experiment = relationship("ResearchExperiment", back_populates="results")


class ResearchPublication(Base):  # type: ignore[misc]
    """Research or projects published when authorised."""
    __tablename__ = "research_publications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    publication_type = Column(Text, nullable=False)  # paper, article, report, software, dataset
    published_at = Column(DateTime(timezone=True), nullable=True)
    is_authorised = Column(Boolean, nullable=False, default=False)
    authorisation_by = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("publication_type IN ('paper', 'article', 'report', 'software', 'dataset')", name="ck_publication_type"),
    )
