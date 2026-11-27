"""Untrusted skill candidates received over P2P."""

import uuid

from sqlalchemy import CheckConstraint, Column, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class P2PSkillCandidate(Base):
    __tablename__ = "p2p_skill_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    envelope_id = Column(Text, nullable=False, unique=True, index=True)
    publisher = Column(Text, nullable=False)
    skill_id = Column(Text, nullable=False)
    version = Column(Text, nullable=False)
    instructions = Column(Text, nullable=False)
    permissions = Column(JSON, nullable=False, default=list)
    checksum = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="candidate")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('candidate', 'approved', 'rejected')",
            name="ck_p2p_skill_candidate_status",
        ),
    )
