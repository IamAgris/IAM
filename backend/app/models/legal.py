"""Autonomous legal intelligence and government monitoring (OD-31).

Legal research is not legal advice. Every change keeps evidence, lifecycle
stage and approval/reference history. IAM cannot create legal authority for
itself or enter binding commitments without authorisation.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base

LIFECYCLE = "discover,authenticate,understand,assess,recommend,authorise,implement,verify"


class LegalSource(Base):  # type: ignore[misc]
    __tablename__ = "legal_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    jurisdiction = Column(Text, nullable=False)
    authority_type = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    feed_url = Column(Text, nullable=True)
    reliability = Column(Text, nullable=False, default="official")
    is_active = Column(Boolean, nullable=False, default=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    last_content_hash = Column(Text, nullable=True)
    terms_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "authority_type IN ('government', 'parliament', 'court', 'regulator', "
            "'central_bank', 'tax_authority', 'international', 'security_authority')",
            name="ck_legal_source_authority_type",
        ),
    )


class LegalInstrument(Base):  # type: ignore[misc]
    __tablename__ = "legal_instruments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("legal_sources.id", ondelete="RESTRICT"),
        nullable=False,
    )
    jurisdiction = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    authority_name = Column(Text, nullable=False)
    instrument_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="announcement")
    official_url = Column(Text, nullable=False)
    document_hash = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    effective_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "instrument_type IN ('constitution', 'legislation', 'regulation', 'court_judgment', "
            "'guidance', 'policy', 'bill', 'draft_regulation', 'treaty', 'standard', 'announcement')",
            name="ck_legal_instrument_type",
        ),
        CheckConstraint(
            "status IN ('proposed', 'draft', 'enacted', 'guidance', 'announcement', 'repealed')",
            name="ck_legal_instrument_status",
        ),
    )


class LegalVersion(Base):  # type: ignore[misc]
    __tablename__ = "legal_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("legal_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_label = Column(Text, nullable=False)
    document_hash = Column(Text, nullable=False)
    content = Column(JSON, nullable=False, default=dict)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LegalChange(Base):  # type: ignore[misc]
    __tablename__ = "legal_changes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instrument_id = Column(
        UUID(as_uuid=True),
        ForeignKey("legal_instruments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    change_type = Column(Text, nullable=False, default="new")
    severity = Column(Text, nullable=False, default="informational")
    lifecycle_stage = Column(Text, nullable=False, default="discover")
    authenticated = Column(Boolean, nullable=False, default=False)
    evidence = Column(JSON, nullable=False, default=dict)
    creator_approval_reference = Column(Text, nullable=True)
    professional_review_reference = Column(Text, nullable=True)
    implemented_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "change_type IN ('new', 'amendment', 'repeal', 'correction')",
            name="ck_legal_change_type",
        ),
        CheckConstraint(
            "severity IN ('critical', 'important', 'informational')",
            name="ck_legal_change_severity",
        ),
        CheckConstraint(
            "lifecycle_stage IN (" + ",".join(f"'{s}'" for s in LIFECYCLE.split(",")) + ")",
            name="ck_legal_change_stage",
        ),
    )


class LegalImpact(Base):  # type: ignore[misc]
    __tablename__ = "legal_impacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_id = Column(
        UUID(as_uuid=True),
        ForeignKey("legal_changes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    affected_system = Column(Text, nullable=False)
    assessment = Column(Text, nullable=False)
    risk_level = Column(Text, nullable=False, default="low")
    recommendation = Column(Text, nullable=False)
    obligations = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('low', 'medium', 'high', 'critical')",
            name="ck_legal_impact_risk_level",
        ),
    )
