"""Public records, vital events and estate research (OD-30).

Every record keeps provenance, status, confidence and correction history.
Public availability is never treated as permission to bypass access controls.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class PublicSource(Base):  # type: ignore[misc]
    __tablename__ = "public_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    jurisdiction = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    access_condition = Column(Text, nullable=False, default="public")
    reliability = Column(Text, nullable=False, default="unverified")
    terms_url = Column(Text, nullable=True)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "access_condition IN ('public', 'requires_authority', 'restricted', 'paid', 'unknown')",
            name="ck_public_source_access_condition",
        ),
        CheckConstraint(
            "reliability IN ('official', 'independent', 'self_reported', 'unverified')",
            name="ck_public_source_reliability",
        ),
    )


class PublicRecord(Base):  # type: ignore[misc]
    __tablename__ = "public_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    category = Column(Text, nullable=False)
    jurisdiction = Column(Text, nullable=False)
    subject_name = Column(Text, nullable=True)
    title = Column(Text, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), nullable=True)
    source_url = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False)
    facts = Column(JSON, nullable=False, default=dict)
    status = Column(Text, nullable=False, default="uncertain")
    confidence = Column(Float, nullable=False, default=0.5)
    legal_authority_reference = Column(Text, nullable=True)
    is_statistical = Column(Boolean, nullable=False, default=False)
    is_correction = Column(Boolean, nullable=False, default=False)
    supersedes_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('verified', 'self_reported', 'uncertain', 'allegation', 'restricted')",
            name="ck_public_record_status",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_public_record_confidence"),
    )


class RecordRelationship(Base):  # type: ignore[misc]
    __tablename__ = "record_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_record_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False, default=dict)
    confidence = Column(Float, nullable=False, default=0.5)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "relation_type IN ('same_entity', 'related_entity', 'conflict', 'correction')",
            name="ck_record_relationship_type",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_record_relationship_confidence"),
    )
