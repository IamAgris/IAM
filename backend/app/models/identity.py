"""Identity module SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class AIIdentity(Base):  # type: ignore[misc]
    __tablename__ = "ai_identity"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    avatar_url = Column(Text, nullable=True)
    communication_preferences = Column(JSON, nullable=False, default=dict)
    interests = Column(JSON, nullable=False, default=list)
    personal_goals = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    personality = relationship("AIPersonality", back_populates="identity", uselist=False, cascade="all, delete-orphan")
    history = relationship("IdentityHistory", back_populates="identity", cascade="all, delete-orphan")


class AIPersonality(Base):  # type: ignore[misc]
    __tablename__ = "ai_personality"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identity_id = Column(UUID(as_uuid=True), ForeignKey("ai_identity.id", ondelete="CASCADE"), nullable=False)
    traits = Column(JSON, nullable=False, default=dict)
    tone = Column(Text, nullable=True)
    formality_level = Column(Integer, nullable=False, default=5)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("formality_level BETWEEN 1 AND 10", name="ck_personality_formality_level"),
    )

    identity = relationship("AIIdentity", back_populates="personality")


class IdentityHistory(Base):  # type: ignore[misc]
    __tablename__ = "identity_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identity_id = Column(UUID(as_uuid=True), ForeignKey("ai_identity.id", ondelete="CASCADE"), nullable=False)
    change_type = Column(Text, nullable=False)
    previous_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reason = Column(Text, nullable=True)

    identity = relationship("AIIdentity", back_populates="history")
