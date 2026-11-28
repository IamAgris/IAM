"""Life management module SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AIIdentityGenesis(Base):  # type: ignore[misc]
    """Permanent, immutable IAM identity genesis record (OD-01)."""
    __tablename__ = "iam_identity_genesis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    permanent_id = Column(Text, nullable=False, unique=True)  # ULID — never changes
    public_name = Column(Text, nullable=False)
    full_name = Column(Text, nullable=True)
    origin_config = Column(JSON, nullable=False, default=dict)
    initial_capabilities = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LifeCycle(Base):  # type: ignore[misc]
    """Daily self-management cycle states."""
    __tablename__ = "life_cycles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cycle_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    state = Column(Text, nullable=False, default="idle")  # idle, working, researching, learning, resting, conserving
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    activities_completed = Column(JSON, nullable=False, default=list)
    resources_consumed = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint("state IN ('idle', 'working', 'researching', 'learning', 'resting', 'conserving')", name="ck_lifecycle_state"),
    )


class DailyRoutine(Base):  # type: ignore[misc]
    """Recurring daily self-management patterns."""
    __tablename__ = "daily_routines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    time_of_day = Column(Text, nullable=False)  # e.g. "09:00", "22:00"
    activity_type = Column(Text, nullable=False)
    duration_minutes = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class LifeHistory(Base):  # type: ignore[misc]
    """Chronological record of important experiences, decisions, achievements."""
    __tablename__ = "life_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(Text, nullable=False)  # decision, achievement, milestone, setback, recovery
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    significance = Column(Integer, nullable=False, default=5)  # 1-10
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    related_memory_ids = Column(JSON, nullable=False, default=list)
    related_goal_ids = Column(JSON, nullable=False, default=list)

    __table_args__ = (
        CheckConstraint("significance BETWEEN 1 AND 10", name="ck_life_history_significance"),
    )


class GoalLifecycle(Base):  # type: ignore[misc]
    """Long-term goal tracking over weeks/months/years."""
    __tablename__ = "goal_lifecycles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    phase = Column(Text, nullable=False, default="planning")  # planning, active, paused, completed, abandoned
    priority = Column(Integer, nullable=False, default=5)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    next_review_at = Column(DateTime(timezone=True), nullable=True)
    progress_percentage = Column(Numeric(5, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("phase IN ('planning', 'active', 'paused', 'completed', 'abandoned')", name="ck_goal_lifecycle_phase"),
        CheckConstraint("priority BETWEEN 1 AND 10", name="ck_goal_lifecycle_priority"),
        CheckConstraint("progress_percentage BETWEEN 0 AND 100", name="ck_goal_lifecycle_progress"),
    )

    goal = relationship("Goal")
