"""Human Public Presence Intelligence (OD-30 / PPIICE).

Research only information a person or reliable public source has openly
published. Public presence is not proof of real-world identity. No private
conversations, credentials, visitor memory or de-anonymisation is involved.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base

STATUSES = "verified,self_reported,uncertain,corrected"


class PublicPerson(Base):  # type: ignore[misc]
    __tablename__ = "public_people"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    canonical_name = Column(Text, nullable=False, index=True)
    internal_public_id = Column(Text, nullable=False, unique=True)
    notes = Column(Text, nullable=True)
    deanonymized = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("deanonymized = FALSE", name="ck_public_person_no_deanonymization"),
    )


class PublicProfile(Base):  # type: ignore[misc]
    __tablename__ = "public_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public_people.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_name = Column(Text, nullable=False)
    source_url = Column(Text, nullable=False)
    source_domain = Column(Text, nullable=False)
    profile_type = Column(Text, nullable=False, default="personal_site")
    stated_name = Column(Text, nullable=True)
    role = Column(Text, nullable=True)
    organization = Column(Text, nullable=True)
    bio = Column(Text, nullable=True)
    interests = Column(JSON, nullable=False, default=list)
    status = Column(Text, nullable=False, default="self_reported")
    confidence = Column(Float, nullable=False, default=0.5)
    content_hash = Column(Text, nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    retrieved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN (" + ",".join(f"'{s}'" for s in STATUSES.split(",")) + ")",
            name="ck_public_profile_status",
        ),
    )


class PresenceClaim(Base):  # type: ignore[misc]
    __tablename__ = "presence_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public_people.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    claim_type = Column(Text, nullable=False)
    value = Column(JSON, nullable=False, default=dict)
    status = Column(Text, nullable=False, default="uncertain")
    confidence = Column(Float, nullable=False, default=0.5)
    source_url = Column(Text, nullable=True)
    first_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    supersedes_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_presence_claim_confidence"),
    )


class IdentityMatch(Base):  # type: ignore[misc]
    __tablename__ = "identity_matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public_people.id", ondelete="CASCADE"),
        nullable=False,
    )
    other_person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public_people.id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence = Column(JSON, nullable=False, default=dict)
    confidence = Column(Float, nullable=False, default=0.5)
    result = Column(Text, nullable=False, default="uncertain")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("result IN ('same', 'uncertain', 'rejected')", name="ck_identity_match_result"),
    )


class PublicRelationship(Base):  # type: ignore[misc]
    __tablename__ = "public_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public_people.id", ondelete="CASCADE"),
        nullable=False,
    )
    related_person_id = Column(UUID(as_uuid=True), nullable=True)
    organization_name = Column(Text, nullable=True)
    relationship_type = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=False, default=dict)
    confidence = Column(Float, nullable=False, default=0.5)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
