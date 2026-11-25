"""Autonomy module SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Goal(Base):
    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="active")
    priority = Column(Integer, nullable=False, default=5)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    target_completion_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'completed', 'abandoned')", name="ck_goal_status"),
        CheckConstraint("priority BETWEEN 1 AND 10", name="ck_goal_priority"),
    )

    plans = relationship("Plan", back_populates="goal", cascade="all, delete-orphan")


class Plan(Base):
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id = Column(UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    title = Column(Text, nullable=False)
    steps = Column(JSON, nullable=False, default=list)
    status = Column(Text, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'failed')", name="ck_plan_status"),
    )

    goal = relationship("Goal", back_populates="plans")
    tasks = relationship("Task", back_populates="plan", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    tool_used = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'failed', 'blocked')", name="ck_task_status"),
    )

    plan = relationship("Plan", back_populates="tasks")
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")


class TaskExecution(Base):
    __tablename__ = "task_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    status = Column(Text, nullable=False)
    output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("status IN ('success', 'failure', 'partial')", name="ck_task_execution_status"),
    )

    task = relationship("Task", back_populates="executions")


class DecisionRecord(Base):
    __tablename__ = "decision_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    decision = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=True)
    confidence = Column(Numeric(3, 2), nullable=False, default=0.5)
    outcome = Column(Text, nullable=True)
    made_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_decision_confidence"),
    )


class ToolRegistry(Base):
    __tablename__ = "tool_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    permissions = relationship("ToolPermission", back_populates="tool", cascade="all, delete-orphan")


class ToolPermission(Base):
    __tablename__ = "tool_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tool_registry.id", ondelete="CASCADE"), nullable=False)
    permission_level = Column(Text, nullable=False)
    requires_human_approval = Column(Boolean, nullable=False, default=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("permission_level IN ('autonomous', 'authorized', 'explicit', 'blocked')", name="ck_tool_permission_level"),
    )

    tool = relationship("ToolRegistry", back_populates="permissions")


class WorkflowCheckpoint(Base):
    __tablename__ = "workflow_checkpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(Text, nullable=False)
    step_name = Column(Text, nullable=False)
    state = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ScheduledActivity(Base):
    __tablename__ = "scheduled_activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    cron_expression = Column(Text, nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
