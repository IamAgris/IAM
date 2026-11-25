"""Audit records for Skill Runtime invocations."""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class SkillRuntimeExecution(Base):
    __tablename__ = "skill_runtime_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_id = Column(Text, nullable=False, index=True)
    permission = Column(Text, nullable=False)
    script = Column(Text, nullable=True)
    caller = Column(Text, nullable=False, default="iam")
    adapter = Column(Text, nullable=False, default="stub")
    status = Column(Text, nullable=False, default="completed")
    dry_run = Column(Boolean, nullable=False, default=True)
    result = Column(JSON, nullable=False, default=dict)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    logs = relationship(
        "SkillRuntimeLog", back_populates="execution", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'denied', 'failed')",
            name="ck_skill_runtime_status",
        ),
    )


class SkillRuntimeLog(Base):
    """Captured stdout/stderr for one Skill Runtime invocation."""

    __tablename__ = "skill_runtime_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("skill_runtime_executions.id", ondelete="CASCADE"),
        nullable=False,
    )
    stream = Column(Text, nullable=False)
    content = Column(Text, nullable=False, default="")
    execution = relationship("SkillRuntimeExecution", back_populates="logs")
