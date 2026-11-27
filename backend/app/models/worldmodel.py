"""World model module SQLAlchemy models"""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, DateTime, ForeignKey, CheckConstraint, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class WorldEntity(Base):
    """Internal representation of people, organisations, countries, technologies, etc."""
    __tablename__ = "world_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)  # person, organisation, country, technology, concept, event
    description = Column(Text, nullable=True)
    properties = Column(JSON, nullable=False, default=dict)
    confidence_level = Column(Numeric(3, 2), nullable=False, default=0.5)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("confidence_level BETWEEN 0 AND 1", name="ck_world_entity_confidence"),
        CheckConstraint("entity_type IN ('person', 'organisation', 'country', 'technology', 'concept', 'event')", name="ck_world_entity_type"),
    )

    relationships_as_source = relationship("EntityRelationship", foreign_keys="EntityRelationship.source_entity_id", cascade="all, delete-orphan", overlaps="source_entity")
    relationships_as_target = relationship("EntityRelationship", foreign_keys="EntityRelationship.target_entity_id", cascade="all, delete-orphan", overlaps="target_entity")


class EntityRelationship(Base):
    """Relationships between world entities."""
    __tablename__ = "entity_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id = Column(UUID(as_uuid=True), ForeignKey("world_entities.id", ondelete="CASCADE"), nullable=False)
    target_entity_id = Column(UUID(as_uuid=True), ForeignKey("world_entities.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(Text, nullable=False)  # works_for, founded, located_in, causes, influences, etc.
    strength = Column(Numeric(3, 2), nullable=False, default=1.0)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("strength BETWEEN 0 AND 1", name="ck_entity_relationship_strength"),
    )

    source_entity = relationship("WorldEntity", foreign_keys=[source_entity_id], overlaps="relationships_as_source")
    target_entity = relationship("WorldEntity", foreign_keys=[target_entity_id], overlaps="relationships_as_target")


class CauseEffectChain(Base):
    """Tracked cause-and-effect relationships for decision reasoning."""
    __tablename__ = "cause_effect_chains"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cause_description = Column(Text, nullable=False)
    effect_description = Column(Text, nullable=False)
    confidence = Column(Numeric(3, 2), nullable=False, default=0.5)
    evidence = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_cause_effect_confidence"),
    )


class WorldEvent(Base):
    """Tracked world events and changing circumstances."""
    __tablename__ = "world_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    occurred_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    relevance_to_iam = Column(Numeric(3, 2), nullable=False, default=0.5)
    related_entity_ids = Column(JSON, nullable=False, default=list)

    __table_args__ = (
        CheckConstraint("relevance_to_iam BETWEEN 0 AND 1", name="ck_world_event_relevance"),
    )


class CapabilityLimitation(Base):
    """IAM's own capabilities and limitations tracking."""
    __tablename__ = "capability_limitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capability_name = Column(Text, nullable=False)
    proficiency_level = Column(Integer, nullable=False, default=0)
    limitation_description = Column(Text, nullable=True)
    last_assessed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    assessment_method = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("proficiency_level BETWEEN 0 AND 100", name="ck_capability_limitation_level"),
    )
