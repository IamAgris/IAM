"""IICS foundation records — egress decisions, source rights, action ledger and QA.

Pending proposal (docs/IAM_IICS_GAP_CLOSURE_ADDENDUM.md): overlay modules inside
existing systems. Nothing here creates a new top-level system or queue.
"""

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class IICSSource(Base):  # type: ignore[misc]
    """A web/API/document source with rights, freshness and legal provenance."""

    __tablename__ = "iics_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False, unique=True, index=True)
    domain = Column(Text, nullable=False, index=True)
    source_type = Column(Text, nullable=False, default="public_web")
    licence = Column(Text, nullable=True)
    rights = Column(JSON, nullable=False, default=dict)
    territory = Column(Text, nullable=True)
    freshness_class = Column(Text, nullable=False, default="documentation")
    reliability_score = Column(Numeric(5, 4), nullable=False, default=0)
    conditions = Column(JSON, nullable=False, default=list)
    legal_audit_event_id = Column(Text, nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "source_type IN ('public_web', 'api', 'document', 'feed')",
            name="ck_iics_source_type",
        ),
        CheckConstraint(
            "freshness_class IN ('volatile', 'documentation', 'standard', 'stable')",
            name="ck_iics_freshness_class",
        ),
    )


class IICSClaim(Base):  # type: ignore[misc]
    """A claim extracted from a source, with confidence and a claim label."""

    __tablename__ = "iics_claims"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True),
        ForeignKey("iics_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim = Column(Text, nullable=False)
    locator = Column(Text, nullable=True)
    publication_date = Column(Text, nullable=True)
    retrieved_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False, default=0)
    label = Column(Text, nullable=False, default="unverified")

    __table_args__ = (
        CheckConstraint(
            "label IN ('verified', 'provisional', 'unverified', "
            "'outdated', 'contradicted', 'unresolved')",
            name="ck_iics_claim_label",
        ),
    )


class IICSAction(Base):  # type: ignore[misc]
    """Append-only cross-service external action record (OD-08 ARQ compatible)."""

    __tablename__ = "iics_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor = Column(Text, nullable=False)
    tool = Column(Text, nullable=False)
    target = Column(Text, nullable=False)
    scope = Column(Text, nullable=False, default="public")
    permission_source = Column(Text, nullable=False, default="legal_gateway")
    approval_ref = Column(Text, nullable=True)
    idempotency_key = Column(String(128), nullable=False, unique=True, index=True)
    status = Column(Text, nullable=False, default="planned")
    verification_result = Column(JSON, nullable=False, default=dict)
    bytes_transferred = Column(Integer, nullable=False, default=0)
    cost_units = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "scope IN ('public', 'authenticated', 'financial', 'protected_core')",
            name="ck_iics_action_scope",
        ),
        CheckConstraint(
            "status IN ('planned', 'executing', 'verified', 'failed', 'cancelled')",
            name="ck_iics_action_status",
        ),
    )


class IICSScheduledTask(Base):  # type: ignore[misc]
    """A governed recurring research job on the OD-08 ARQ runtime."""

    __tablename__ = "iics_scheduled_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(128), nullable=False, unique=True, index=True)
    goal = Column(Text, nullable=False)
    query = Column(Text, nullable=False)
    freshness_class = Column(Text, nullable=False, default="documentation")
    cadence_minutes = Column(Integer, nullable=False, default=1440)
    next_run_at = Column(DateTime(timezone=True), nullable=False)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Text, nullable=False, default="scheduled")
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'running', 'completed', 'failed', 'paused', 'cancelled')",
            name="ck_iics_scheduled_status",
        ),
    )


class IICSAdvisory(Base):  # type: ignore[misc]
    """A deduplicated external security advisory (CVE/OSV/NVD)."""

    __tablename__ = "iics_advisories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cve_id = Column(Text, nullable=False, unique=True, index=True)
    source = Column(Text, nullable=False, default="osv")
    severity = Column(Text, nullable=False, default="UNKNOWN")
    published = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    summary = Column(Text, nullable=False, default="")
    affected = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IICSDLPEvent(Base):  # type: ignore[misc]
    """A blocked or flagged egress attempt from the cross-channel DLP engine."""

    __tablename__ = "iics_dlp_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel = Column(Text, nullable=False)
    matched_labels = Column(JSON, nullable=False, default=list)
    action = Column(Text, nullable=False, default="blocked")
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IICSSitePolicy(Base):  # type: ignore[misc]
    """Versioned snapshot of robots/terms for a domain with TTL and hash."""

    __tablename__ = "iics_site_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(Text, nullable=False, unique=True, index=True)
    robots_text = Column(Text, nullable=False, default="")
    terms_text = Column(Text, nullable=False, default="")
    content_hash = Column(String(64), nullable=False)
    ttl_hours = Column(Integer, nullable=False, default=720)
    source_url = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IICSPrivacyRecord(Base):  # type: ignore[misc]
    """DSAR, consent-withdrawal and cross-border transfer evidence."""

    __tablename__ = "iics_privacy_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind = Column(Text, nullable=False, index=True)
    subject_ref = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="open")
    jurisdiction = Column(Text, nullable=True)
    details = Column(JSON, nullable=False, default=dict)
    evidence = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('dsar_access', 'dsar_erasure', 'consent_withdrawal', 'transfer_assessment')",
            name="ck_iics_privacy_kind",
        ),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'resolved', 'refused')",
            name="ck_iics_privacy_status",
        ),
    )


class IICSBenchmarkResult(Base):  # type: ignore[misc]
    """A scored internet-capability benchmark run with a pass/fail gate."""

    __tablename__ = "iics_benchmark_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    benchmark = Column(Text, nullable=False, index=True)
    score = Column(Numeric(5, 4), nullable=False)
    threshold = Column(Numeric(5, 4), nullable=False)
    passed = Column(Boolean, nullable=False)
    evidence = Column(JSON, nullable=False, default=dict)
    run_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
