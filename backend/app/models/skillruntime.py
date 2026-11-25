"""Audit records for Skill Runtime invocations."""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
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

    __table_args__ = (
        CheckConstraint(
            "status IN ('completed', 'denied', 'failed')",
            name="ck_skill_runtime_status",
        ),
    )
