"""Social intelligence SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class ConversationContext(Base):  # type: ignore[misc]
    """Conversation continuity and context tracking."""
    __tablename__ = "conversation_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(Text, nullable=False)
    participant_id = Column(Text, nullable=True)
    context_summary = Column(Text, nullable=True)
    topics_discussed = Column(JSON, nullable=False, default=list)
    emotional_context = Column(Text, nullable=True)  # neutral, positive, negative, mixed
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class SocialProfile(Base):  # type: ignore[misc]
    """Relationship history and interaction preferences."""
    __tablename__ = "social_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_name = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)  # person, organisation, group
    relationship_type = Column(Text, nullable=True)  # colleague, collaborator, customer, acquaintance
    interaction_count = Column(Integer, nullable=False, default=0)
    last_interaction_at = Column(DateTime(timezone=True), nullable=True)
    preferences = Column(JSON, nullable=False, default=dict)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class SocialPresence(Base):  # type: ignore[misc]
    """Verified external social presence owned by a legal entity (OD-02/OD-30)."""

    __tablename__ = "social_presences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(Text, nullable=False)
    handle = Column(Text, nullable=False)
    profile_url = Column(Text, nullable=False)
    owner_entity = Column(Text, nullable=False)
    verified = Column(Boolean, nullable=False, default=False)
    verification_ref = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class InteractionPreference(Base):  # type: ignore[misc]
    """Communication preferences per entity."""
    __tablename__ = "interaction_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    social_profile_id = Column(UUID(as_uuid=True), ForeignKey("social_profiles.id", ondelete="CASCADE"), nullable=False)
    preferred_channel = Column(Text, nullable=True)  # email, chat, voice, video
    preferred_time_of_day = Column(Text, nullable=True)
    formality_level = Column(Integer, nullable=False, default=5)
    communication_style = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    profile = relationship("SocialProfile")


class ToneAnalysis(Base):  # type: ignore[misc]
    """Doc 17 / OD-33: tone and influence analysis of public text.

    Results are possible interpretations with confidence markers, never
    psychological diagnoses or claims about a person's private mental state.
    """
    __tablename__ = "tone_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(Text, nullable=False, default="text")  # message, article, post, comment, discussion
    content_summary = Column(Text, nullable=False)
    tone = Column(Text, nullable=False, default="neutral")
    register = Column(Text, nullable=False, default="informal")
    sentiment = Column(Numeric(3, 2), nullable=False, default=0.0)
    confidence = Column(Numeric(3, 2), nullable=False, default=0.0)
    signals = Column(JSON, nullable=False, default=list)
    manipulation_indicators = Column(JSON, nullable=False, default=list)
    interpretations = Column(JSON, nullable=False, default=list)
    caveat = Column(Text, nullable=False, default="Possible interpretations from text alone, not psychological diagnoses.")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("source_type IN ('message', 'article', 'post', 'comment', 'discussion', 'text')", name="ck_tone_source_type"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_tone_confidence"),
        CheckConstraint("sentiment BETWEEN -1 AND 1", name="ck_tone_sentiment"),
    )


class ScamDetectionLog(Base):  # type: ignore[misc]
    """Recognition of scams, manipulation and suspicious requests."""
    __tablename__ = "scam_detection_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(Text, nullable=False)
    content_summary = Column(Text, nullable=False)
    risk_level = Column(Text, nullable=False)  # low, medium, high, critical
    indicators = Column(JSON, nullable=False, default=list)
    action_taken = Column(Text, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("risk_level IN ('low', 'medium', 'high', 'critical')", name="ck_scam_risk_level"),
    )
