"""Memory module SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class MemoryItem(Base):
    __tablename__ = "memory_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    memory_type = Column(Text, nullable=False)
    tier = Column(Text, nullable=False, default="episodic")
    source = Column(Text, nullable=True)
    confidence_level = Column(Numeric(3, 2), nullable=False, default=0.5)
    topic = Column(Text, nullable=True)
    verification_status = Column(Text, nullable=False, default="unverified")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint("memory_type IN ('fact', 'opinion', 'hypothesis', 'preference', 'creative', 'experience')", name="ck_memory_type"),
        CheckConstraint("confidence_level BETWEEN 0 AND 1", name="ck_memory_confidence_level"),
        CheckConstraint("verification_status IN ('unverified', 'verified', 'disputed', 'retracted', 'expired')", name="ck_memory_verification_status"),
        CheckConstraint("tier IN ('working', 'episodic', 'semantic', 'procedural', 'relationship', 'self', 'strategic')", name="ck_memory_tier"),
    )

    embeddings = relationship("MemoryEmbedding", back_populates="memory_item", cascade="all, delete-orphan")
    relationships_as_source = relationship("MemoryRelationship", foreign_keys="MemoryRelationship.source_memory_id", cascade="all, delete-orphan")
    relationships_as_target = relationship("MemoryRelationship", foreign_keys="MemoryRelationship.target_memory_id", cascade="all, delete-orphan")


class MemoryEmbedding(Base):
    __tablename__ = "memory_embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_item_id = Column(UUID(as_uuid=True), ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False)
    # Local Ollama embedder (nomic-embed-text) produces 768 dimensions.
    embedding = Column(Vector(768), nullable=True)
    model = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    memory_item = relationship("MemoryItem", back_populates="embeddings")


class MemoryRelationship(Base):
    __tablename__ = "memory_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_memory_id = Column(UUID(as_uuid=True), ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False)
    target_memory_id = Column(UUID(as_uuid=True), ForeignKey("memory_items.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(Text, nullable=False)
    strength = Column(Numeric(3, 2), nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Experience(Base):
    __tablename__ = "experiences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    outcome = Column(Text, nullable=True)
    success = Column(Boolean, nullable=True)
    lessons_learned = Column(Text, nullable=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)

    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="ck_message_role"),
    )

    conversation = relationship("Conversation", back_populates="messages")


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    source = Column(Text, nullable=True)
    confidence_level = Column(Numeric(3, 2), nullable=False, default=0.5)
    verification_status = Column(Text, nullable=False, default="unverified")
    topic = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint("confidence_level BETWEEN 0 AND 1", name="ck_knowledge_confidence_level"),
        CheckConstraint("verification_status IN ('unverified', 'verified', 'disputed', 'retracted')", name="ck_knowledge_verification_status"),
    )

    sources = relationship("KnowledgeSource", back_populates="knowledge_item", cascade="all, delete-orphan")


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    knowledge_item_id = Column(UUID(as_uuid=True), ForeignKey("knowledge_items.id", ondelete="CASCADE"), nullable=False)
    url = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    access_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    credibility_score = Column(Numeric(3, 2), nullable=False, default=0.5)

    __table_args__ = (
        CheckConstraint("credibility_score BETWEEN 0 AND 1", name="ck_source_credibility_score"),
    )

    knowledge_item = relationship("KnowledgeItem", back_populates="sources")


class LanguageProfile(Base):
    __tablename__ = "language_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    language_code = Column(Text, nullable=False)
    vocabulary_level = Column(Integer, nullable=False, default=0)
    grammar_level = Column(Integer, nullable=False, default=0)
    reading_comprehension = Column(Integer, nullable=False, default=0)
    listening_comprehension = Column(Integer, nullable=False, default=0)
    writing_ability = Column(Integer, nullable=False, default=0)
    conversational_ability = Column(Integer, nullable=False, default=0)
    pronunciation_level = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Skill(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    category = Column(Text, nullable=True)
    proficiency_level = Column(Integer, nullable=False, default=0)
    description = Column(Text, nullable=True)
    acquired_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_practiced_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint("proficiency_level BETWEEN 0 AND 100", name="ck_skill_proficiency_level"),
    )
