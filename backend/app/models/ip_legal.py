"""IP & Legal Intelligence (IPLCI) governance models — proposed OD-48.

These tables are distinct from the OD-31 legal-intelligence tables
(``legal_sources``, ``legal_instruments`` …) and from the existing
``ip_records`` / ``asset_licences`` owned-asset records. They hold the
rights-assessment, permission, provenance, lineage and append-only evidence
records required by the IPLCI master specification (§4).
"""

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    JSON,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base

RIGHTS_STATUSES = (
    "PUBLIC_DOMAIN", "OPEN_LICENCE", "CREATIVE_COMMONS",
    "COMMERCIAL_LICENCE", "COPYRIGHT_PROTECTED", "UNKNOWN_OWNERSHIP",
)
SOURCE_CLASSES = (
    "OPEN_RESEARCH", "REFERENCE_ONLY", "LICENSED_RESEARCH",
    "RESTRICTED_RESEARCH", "CONFIDENTIAL", "UNVERIFIED", "PROHIBITED",
)
PERMISSION_STATES = ("PERMITTED", "PROHIBITED", "UNKNOWN")
SOURCE_STATES = (
    "NOT_VALIDATED", "APPROVED", "RESTRICTED",
    "QUARANTINED", "REVOKED", "EXPIRED", "BLOCKED",
)
DECISION_CLASSES = ("LOW", "MODERATE", "HIGH", "CRITICAL", "UNKNOWN")
ASSESSMENT_RESULTS = (
    "APPROVED", "CONDITIONAL", "BLOCKED",
    "QUARANTINED", "REVOKED", "EXPIRED",
)


def _in(values: tuple[str, ...] | list[str]) -> str:
    return ",".join(f"'{value}'" for value in values)


class IPLegalParty(Base):  # type: ignore[misc]
    __tablename__ = "ip_legal_parties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    party_type = Column(Text, nullable=False, default="third_party")
    contact_ref = Column(Text, nullable=True)
    authority_evidence = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "party_type IN ('person','entity','creator','iam','third_party')",
            name="ck_ip_legal_party_type",
        ),
    )


class IPLegalSource(Base):  # type: ignore[misc]
    """A discovered/collected resource with provenance and rights posture."""

    __tablename__ = "ip_legal_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uri = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), nullable=True)
    author = Column(Text, nullable=True)
    publisher = Column(Text, nullable=True)
    acquisition_method = Column(Text, nullable=False, default="other")
    collection_method = Column(Text, nullable=True)
    collected_at = Column(DateTime(timezone=True), nullable=True)
    rights_status = Column(Text, nullable=False, default="UNKNOWN_OWNERSHIP")
    source_class = Column(Text, nullable=False, default="UNVERIFIED")
    jurisdiction = Column(Text, nullable=True)
    permission_evidence = Column(Text, nullable=True)
    licence_id = Column(UUID(as_uuid=True), nullable=True)
    expiry_date = Column(DateTime(timezone=True), nullable=True)
    revocation_conditions = Column(Text, nullable=True)
    permission_withdrawn = Column(Boolean, nullable=False, default=False)
    territory = Column(JSON, nullable=True)
    personal_data_present = Column(Boolean, nullable=False, default=False)
    privacy_lawful_basis = Column(Text, nullable=True)
    attribution_required = Column(Boolean, nullable=False, default=False)
    licence_flags = Column(JSON, nullable=False, default=dict)
    current_permission_state = Column(Text, nullable=False, default="NOT_VALIDATED")
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(f"rights_status IN ({_in(RIGHTS_STATUSES)})", name="ck_ip_legal_source_rights"),
        CheckConstraint(f"source_class IN ({_in(SOURCE_CLASSES)})", name="ck_ip_legal_source_class"),
        CheckConstraint(f"current_permission_state IN ({_in(SOURCE_STATES)})", name="ck_ip_legal_source_state"),
    )


class IPLegalLicence(Base):  # type: ignore[misc]
    """Licence record with the conditions Phase 1 evaluates."""

    __tablename__ = "ip_legal_licences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    identifier = Column(Text, nullable=False)
    version = Column(Text, nullable=True)
    licence_text_ref = Column(Text, nullable=True)
    commercial_use = Column(Boolean, nullable=True)
    modification = Column(Boolean, nullable=True)
    redistribution = Column(Boolean, nullable=True)
    attribution_required = Column(Boolean, nullable=False, default=False)
    share_alike = Column(Boolean, nullable=False, default=False)
    non_commercial = Column(Boolean, nullable=False, default=False)
    territory = Column(JSON, nullable=True)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalPermission(Base):  # type: ignore[misc]
    """Explicit tri-state permission for one right on one source."""

    __tablename__ = "ip_legal_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    right = Column(Text, nullable=False)
    state = Column(Text, nullable=False, default="UNKNOWN")
    basis = Column(Text, nullable=True)
    conditions = Column(JSON, nullable=False, default=list)
    evidence_ref = Column(Text, nullable=True)
    assessed_by = Column(Text, nullable=True)
    assessed_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            '"right" IN (\'read\',\'analyse\',\'store\',\'reproduce\',\'derive\',\'modify\','
            "'distribute','train','commercialise','disclose')",
            name="ck_ip_legal_permission_right",
        ),
        CheckConstraint(f"state IN ({_in(PERMISSION_STATES)})", name="ck_ip_legal_permission_state"),
    )


class IPLegalAssessment(Base):  # type: ignore[misc]
    """Auditable result of a rights assessment or gateway check."""

    __tablename__ = "ip_legal_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    operation = Column(Text, nullable=False)
    agent_id = Column(Text, nullable=False, default="main")
    decision = Column(Text, nullable=False, default="QUARANTINED")
    decision_class = Column(Text, nullable=False, default="UNKNOWN")
    jurisdiction = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    rules_applied = Column(JSON, nullable=False, default=list)
    evidence_refs = Column(JSON, nullable=False, default=list)
    rights_evaluated = Column(JSON, nullable=False, default=dict)
    conditions = Column(JSON, nullable=False, default=list)
    policy_version = Column(Text, nullable=False, default="1.0")
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(f"decision IN ({_in(ASSESSMENT_RESULTS)})", name="ck_ip_legal_assessment_decision"),
        CheckConstraint(f"decision_class IN ({_in(DECISION_CLASSES)})", name="ck_ip_legal_assessment_class"),
    )


class IPLegalIPAsset(Base):  # type: ignore[misc]
    """Ownership and authorship record for an IP asset (IL-12)."""

    __tablename__ = "ip_legal_ip_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    created_by = Column(Text, nullable=True)
    legal_owner = Column(Text, nullable=False)
    origin = Column(Text, nullable=False, default="iam")
    inventorship = Column(JSON, nullable=True)
    transfer_reference = Column(Text, nullable=True)
    third_party_contributions = Column(JSON, nullable=False, default=list)
    ownership_status = Column(Text, nullable=False, default="unknown")
    registration_status = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "origin IN ('iam','creator','third_party','joint')",
            name="ck_ip_legal_asset_origin",
        ),
        CheckConstraint(
            "ownership_status IN ('owned','licensed','disputed','unknown')",
            name="ck_ip_legal_asset_ownership",
        ),
    )


class IPLegalDatasetProvenance(Base):  # type: ignore[misc]
    """Dataset provenance and training-approval status (IL-10)."""

    __tablename__ = "ip_legal_dataset_provenance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_version = Column(Text, nullable=False)
    source_ids = Column(JSON, nullable=False, default=list)
    assessment_ids = Column(JSON, nullable=False, default=list)
    collection_history = Column(Text, nullable=True)
    privacy_classification = Column(Text, nullable=False, default="unknown")
    permitted_purposes = Column(JSON, nullable=False, default=list)
    retention_policy = Column(Text, nullable=True)
    approval_status = Column(Text, nullable=False, default="pending")
    approved_by = Column(Text, nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "approval_status IN ('pending','approved','rejected','revoked')",
            name="ck_ip_legal_dataset_approval",
        ),
    )


class IPLegalAuditEvent(Base):  # type: ignore[misc]
    """Append-only, hash-chained governance evidence (CE-06)."""

    __tablename__ = "ip_legal_audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence = Column(Integer, nullable=False, unique=True)
    event_type = Column(Text, nullable=False)
    actor = Column(Text, nullable=False, default="sdk")
    resource_id = Column(Text, nullable=True)
    decision = Column(Text, nullable=True)
    policy_version = Column(Text, nullable=False, default="1.0")
    ruleset_version = Column(Text, nullable=False, default="1.0")
    previous_hash = Column(Text, nullable=False)
    event_hash = Column(Text, nullable=False, index=True)
    details = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalTrademark(Base):  # type: ignore[misc]
    """Registered, pending or unregistered mark records (IL-02)."""

    __tablename__ = "ip_legal_trademarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mark_text = Column(Text, nullable=False)
    owner = Column(Text, nullable=False)
    jurisdiction = Column(Text, nullable=True)
    classes = Column(JSON, nullable=False, default=list)
    status = Column(Text, nullable=False, default="registered")
    registration_number = Column(Text, nullable=True)
    goods_services = Column(Text, nullable=True)
    logo_hash = Column(Text, nullable=True)
    territory = Column(JSON, nullable=True)
    filed_at = Column(DateTime(timezone=True), nullable=True)
    registered_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('registered','pending','unregistered','withdrawn','expired')",
            name="ck_ip_legal_trademark_status",
        ),
    )


class IPLegalPatent(Base):  # type: ignore[misc]
    """Patent publications and claim records (IL-03)."""

    __tablename__ = "ip_legal_patents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    publication_number = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    owner = Column(Text, nullable=True)
    jurisdiction = Column(JSON, nullable=False, default=list)
    status = Column(Text, nullable=False, default="pending")
    claims = Column(JSON, nullable=False, default=list)
    filed_at = Column(DateTime(timezone=True), nullable=True)
    priority_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    family_id = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('active','granted','pending','expired','lapsed','withdrawn')",
            name="ck_ip_legal_patent_status",
        ),
    )


class IPLegalDesignRight(Base):  # type: ignore[misc]
    """Industrial designs and other registered design-like rights (IL-04)."""

    __tablename__ = "ip_legal_design_rights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    right_type = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    owner = Column(Text, nullable=True)
    jurisdiction = Column(Text, nullable=True)
    registration_number = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="unregistered")
    expires_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "right_type IN ('industrial_design','unregistered_design',"
            "'geographical_indication','plant_variety','semiconductor_layout','domain_name')",
            name="ck_ip_legal_design_type",
        ),
    )


class IPLegalDependency(Base):  # type: ignore[misc]
    """A software dependency with its licence and ownership provenance (IL-09)."""

    __tablename__ = "ip_legal_dependencies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Text, nullable=False, index=True)
    name = Column(Text, nullable=False)
    version = Column(Text, nullable=True)
    licence_id = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    origin = Column(Text, nullable=False, default="third_party")
    vulnerability_status = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "origin IN ('original','third_party','ai_generated','copied_public',"
            "'generated_from_licensed_model','employment_or_contractor','unclear')",
            name="ck_ip_legal_dependency_origin",
        ),
    )


class IPLegalSbom(Base):  # type: ignore[misc]
    """Software bill of materials for a project (IL-09)."""

    __tablename__ = "ip_legal_sboms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(Text, nullable=False, index=True)
    components = Column(JSON, nullable=False, default=list)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalRiskDecision(Base):  # type: ignore[misc]
    """Auditable trademark/patent/design/software risk decision."""

    __tablename__ = "ip_legal_risk_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    jurisdiction = Column(Text, nullable=True)
    risk = Column(Text, nullable=False, default="UNKNOWN")
    outcome = Column(Text, nullable=False)
    reasons = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=list)
    professional_review_required = Column(Boolean, nullable=False, default=False)
    policy_version = Column(Text, nullable=False, default="2.0")
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "risk IN ('LOW','MODERATE','HIGH','CRITICAL','UNKNOWN')",
            name="ck_ip_legal_risk_level",
        ),
    )


class IPLegalCollectionCheck(Base):  # type: ignore[misc]
    """Web-collection legality check (IL-07)."""

    __tablename__ = "ip_legal_collection_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_uri = Column(Text, nullable=False)
    intended_use = Column(Text, nullable=False, default="research")
    risk = Column(Text, nullable=False, default="UNKNOWN")
    outcome = Column(Text, nullable=False)
    blocked = Column(Boolean, nullable=False, default=False)
    flags = Column(JSON, nullable=False, default=dict)
    conditions = Column(JSON, nullable=False, default=list)
    reasons = Column(JSON, nullable=False, default=list)
    policy_version = Column(Text, nullable=False, default="3.0")
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalPrivacyRecord(Base):  # type: ignore[misc]
    """Privacy classification and lawful-basis record (IL-08)."""

    __tablename__ = "ip_legal_privacy_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    jurisdiction = Column(Text, nullable=False, default="ZA")
    personal_data_present = Column(Boolean, nullable=False, default=False)
    data_categories = Column(JSON, nullable=False, default=list)
    lawful_basis = Column(Text, nullable=True)
    explicit_consent = Column(Boolean, nullable=False, default=False)
    dpia_completed = Column(Boolean, nullable=False, default=False)
    minimisation_applied = Column(Boolean, nullable=False, default=False)
    retention_period = Column(Text, nullable=True)
    deletion_supported = Column(Boolean, nullable=False, default=False)
    deletion_requested = Column(Boolean, nullable=False, default=False)
    deletion_completed = Column(Boolean, nullable=False, default=False)
    dsar_requested = Column(Boolean, nullable=False, default=False)
    dsar_completed = Column(Boolean, nullable=False, default=False)
    international_transfer = Column(Boolean, nullable=False, default=False)
    transfer_mechanism = Column(Text, nullable=True)
    disclosure_permitted = Column(Boolean, nullable=False, default=False)
    risk = Column(Text, nullable=False, default="UNKNOWN")
    outcome = Column(Text, nullable=False, default="quarantined")
    verification_status = Column(Text, nullable=False, default="requires_verification")
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalTrainingApproval(Base):  # type: ignore[misc]
    """Independent training approval (IL-10)."""

    __tablename__ = "ip_legal_training_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    dataset_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    requester = Column(Text, nullable=False, default="main")
    approver = Column(Text, nullable=False)
    ingestion_reviewer = Column(Text, nullable=False)
    decision = Column(Text, nullable=False, default="pending")
    basis = Column(Text, nullable=True)
    purpose = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "decision IN ('pending','approved','rejected','revoked')",
            name="ck_ip_legal_training_approval_decision",
        ),
    )


class IPLegalModelLineage(Base):  # type: ignore[misc]
    """Model lineage and affected-by-revocation status (IL-10 §4.3)."""

    __tablename__ = "ip_legal_model_lineages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(Text, nullable=False, index=True)
    base_model = Column(Text, nullable=False)
    base_model_version = Column(Text, nullable=True)
    base_model_licence = Column(Text, nullable=True)
    dataset_ids = Column(JSON, nullable=False, default=list)
    approval_ids = Column(JSON, nullable=False, default=list)
    training_date = Column(DateTime(timezone=True), nullable=True)
    evaluation_ref = Column(Text, nullable=True)
    promotion_status = Column(Text, nullable=False, default="candidate")
    affected_by_revocation = Column(JSON, nullable=False, default=list)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalJurisdictionRule(Base):  # type: ignore[misc]
    """Contextual legal provision for a jurisdiction/domain (CE-03)."""

    __tablename__ = "ip_legal_jurisdiction_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction = Column(Text, nullable=False, index=True)
    domain = Column(Text, nullable=False)
    provision = Column(Text, nullable=False)
    source_ref = Column(Text, nullable=True)
    verification_status = Column(Text, nullable=False, default="requires_verification")
    effective_from = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalOfficialSource(Base):  # type: ignore[misc]
    """Official legal source register for verification (CE-04)."""

    __tablename__ = "ip_legal_official_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    authority = Column(Text, nullable=False)
    authority_type = Column(Text, nullable=False, default="regulator")
    jurisdiction = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    verified_by = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalKnowledgeVerification(Base):  # type: ignore[misc]
    """Verification record for a legal claim or source provision (IL-17)."""

    __tablename__ = "ip_legal_knowledge_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    claim = Column(Text, nullable=False)
    jurisdiction = Column(Text, nullable=True)
    source_url = Column(Text, nullable=True)
    provision_ref = Column(Text, nullable=True)
    document_type = Column(Text, nullable=False, default="guidance")
    status = Column(Text, nullable=False, default="unverified")
    reviewer = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    checked_at = Column(DateTime(timezone=True), nullable=True)
    reasons = Column(JSON, nullable=False, default=list)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('unverified','requires_verification','verified','superseded')",
            name="ck_ip_legal_knowledge_status",
        ),
    )


class IPLegalObligation(Base):  # type: ignore[misc]
    """Tracked legal obligation and deadline (IL-14/IL-16)."""

    __tablename__ = "ip_legal_obligations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(Text, nullable=False)
    jurisdiction = Column(Text, nullable=True)
    obligation = Column(Text, nullable=False)
    source_ref = Column(Text, nullable=True)
    responsible_party = Column(Text, nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Text, nullable=False, default="open")
    evidence_ref = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('open','in_progress','completed','overdue')",
            name="ck_ip_legal_obligation_status",
        ),
    )


class IPLegalBusinessReview(Base):  # type: ignore[misc]
    """Business/legal operations screening decision (IL-14)."""

    __tablename__ = "ip_legal_business_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    activity = Column(Text, nullable=False)
    business_domain = Column(Text, nullable=False)
    jurisdiction = Column(Text, nullable=True)
    risk = Column(Text, nullable=False, default="UNKNOWN")
    outcome = Column(Text, nullable=False)
    obligations = Column(JSON, nullable=False, default=list)
    blockers = Column(JSON, nullable=False, default=list)
    human_approval_required = Column(Boolean, nullable=False, default=False)
    approval_reference = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalEthicsReview(Base):  # type: ignore[misc]
    """Research-ethics, identity or cross-border review record (IL-19)."""

    __tablename__ = "ip_legal_ethics_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_type = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    jurisdiction = Column(Text, nullable=True)
    risk = Column(Text, nullable=False, default="UNKNOWN")
    outcome = Column(Text, nullable=False)
    requirements = Column(JSON, nullable=False, default=list)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "review_type IN ('research_ethics','identity','cross_border')",
            name="ck_ip_legal_ethics_type",
        ),
    )


class IPLegalDisputeCase(Base):  # type: ignore[misc]
    """An IP complaint, takedown or ownership dispute (IL-15)."""

    __tablename__ = "ip_legal_dispute_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_type = Column(Text, nullable=False)
    complainant = Column(Text, nullable=True)
    claim_ref = Column(Text, nullable=True)
    authority_verified = Column(Boolean, nullable=False, default=False)
    status = Column(Text, nullable=False, default="received")
    affected_assets = Column(JSON, nullable=False, default=list)
    affected_datasets = Column(JSON, nullable=False, default=list)
    affected_models = Column(JSON, nullable=False, default=list)
    evidence_refs = Column(JSON, nullable=False, default=list)
    response_ref = Column(Text, nullable=True)
    deadlines = Column(JSON, nullable=False, default=list)
    outcome = Column(Text, nullable=True)
    case_history = Column(JSON, nullable=False, default=list)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "case_type IN ('copyright','trademark','patent','licence',"
            "'takedown','attribution','ownership')",
            name="ck_ip_legal_dispute_type",
        ),
        CheckConstraint(
            "status IN ('received','verifying','investigating','restricted',"
            "'responded','resolved','withdrawn','appealed')",
            name="ck_ip_legal_dispute_status",
        ),
    )


class IPLegalIncidentCase(Base):  # type: ignore[misc]
    """An incident where improper use or disclosure was discovered (IL-15)."""

    __tablename__ = "ip_legal_incident_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_type = Column(Text, nullable=False)
    detected_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    affected_sources = Column(JSON, nullable=False, default=list)
    affected_projects = Column(JSON, nullable=False, default=list)
    affected_models = Column(JSON, nullable=False, default=list)
    exposure_assessment = Column(Text, nullable=True)
    notification_required = Column(Boolean, nullable=False, default=False)
    notification_decision = Column(Text, nullable=True)
    remediation_ref = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    rules_updated = Column(Boolean, nullable=False, default=False)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalLegalHold(Base):  # type: ignore[misc]
    """Preservation order blocking deletion of relevant evidence (FR-04)."""

    __tablename__ = "ip_legal_legal_holds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reason = Column(Text, nullable=False)
    case_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    scope = Column(JSON, nullable=False, default=list)
    issued_by = Column(Text, nullable=False)
    issued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
    released_by = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)


class IPLegalRightsContact(Base):  # type: ignore[misc]
    """Rights-holder contact and licence negotiation record (IL-15)."""

    __tablename__ = "ip_legal_rights_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    party_id = Column(UUID(as_uuid=True), nullable=True)
    request_type = Column(Text, nullable=False)
    requested_rights = Column(JSON, nullable=False, default=list)
    status = Column(Text, nullable=False, default="requested")
    agreement_ref = Column(Text, nullable=True)
    review_date = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "request_type IN ('permission','licence','renewal','attribution',"
            "'dataset_permission','training_permission')",
            name="ck_ip_legal_contact_request_type",
        ),
        CheckConstraint(
            "status IN ('requested','agreed','rejected','expired','withdrawn')",
            name="ck_ip_legal_contact_status",
        ),
    )


class IPLegalComplianceDeadline(Base):  # type: ignore[misc]
    """Compliance calendar entry (IL-16)."""

    __tablename__ = "ip_legal_compliance_deadlines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deadline_type = Column(Text, nullable=False)
    source_ref = Column(Text, nullable=True)
    jurisdiction = Column(Text, nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)
    notify_before = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="open")
    completed_at = Column(DateTime(timezone=True), nullable=True)
    proof_ref = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "deadline_type IN ('filing','renewal','reporting','retention','dispute',"
            "'registration','review','deletion')",
            name="ck_ip_legal_deadline_type",
        ),
    )


class IPLegalEvidenceRecord(Base):  # type: ignore[misc]
    """Evidence preserved for an assessment, dispute or incident."""

    __tablename__ = "ip_legal_evidence_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    case_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    legal_hold_id = Column(UUID(as_uuid=True), nullable=True)
    source_url = Column(Text, nullable=True)
    document_ref = Column(Text, nullable=True)
    legal_provision_ref = Column(Text, nullable=True)
    licence_version = Column(Text, nullable=True)
    captured_at = Column(DateTime(timezone=True), nullable=True)
    jurisdiction = Column(Text, nullable=True)
    content_hash = Column(Text, nullable=True)
    retention_until = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalContinuityRecord(Base):  # type: ignore[misc]
    """Governance continuity/recovery check result (IL-20)."""

    __tablename__ = "ip_legal_continuity_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_type = Column(Text, nullable=False, default="governance_recovery")
    risk = Column(Text, nullable=False, default="UNKNOWN")
    outcome = Column(Text, nullable=False)
    problems = Column(JSON, nullable=False, default=list)
    recovery_actions = Column(JSON, nullable=False, default=list)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class IPLegalPolicy(Base):  # type: ignore[misc]
    """Signed, versioned compliance policy (P6)."""

    __tablename__ = "ip_legal_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(Text, nullable=False, unique=True)
    rules = Column(JSON, nullable=False, default=dict)
    signed_by = Column(Text, nullable=False)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    signature = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="active")
    change_approval_ref = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','active','retired')",
            name="ck_ip_legal_policy_status",
        ),
    )


class IPLegalValidationTask(Base):  # type: ignore[misc]
    """Qualified-counsel verification task for a legal claim or source."""

    __tablename__ = "ip_legal_validation_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    jurisdiction = Column(Text, nullable=True)
    question = Column(Text, nullable=False)
    official_source_url = Column(Text, nullable=True)
    provision_ref = Column(Text, nullable=True)
    assigned_counsel = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    evidence_ref = Column(Text, nullable=True)
    reviewer_reference = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','in_review','verified','rejected','superseded')",
            name="ck_ip_legal_validation_status",
        ),
    )

