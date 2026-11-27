"""Website knowledge base models (Universal Web Intelligence)."""

from sqlalchemy import Column, String, Text, JSON, Boolean, Integer, BigInteger, DateTime, CheckConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class WebsiteKnowledge(Base):  # type: ignore[misc]
    """Per-website learned knowledge: login procedures, auth methods,
    known restrictions, browser compatibility, verification requirements
    and prior failures. No credentials or secrets are stored here."""

    __tablename__ = "website_knowledge"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(Text, nullable=False, unique=True, index=True)
    display_name = Column(Text, nullable=True)
    homepage_url = Column(Text, nullable=True)
    login_procedure = Column(JSON, nullable=False, default=list)  # ordered steps
    auth_methods = Column(JSON, nullable=False, default=list)  # password, passkey, totp, oauth, saml
    registration_procedure = Column(JSON, nullable=False, default=list)
    supported_passkeys = Column(Boolean, nullable=False, default=False)
    mfa_methods = Column(JSON, nullable=False, default=list)  # totp, hardware_key, sms, email
    known_restrictions = Column(JSON, nullable=False, default=list)  # captcha, paywall, geo_block
    browser_compatibility = Column(JSON, nullable=False, default=list)  # chromium, firefox, webkit
    verification_requirements = Column(JSON, nullable=False, default=list)  # email, sms, id_document
    prior_failures = Column(JSON, nullable=False, default=list)  # failed workflows and reasons
    success_patterns = Column(JSON, nullable=False, default=list)  # successful workflows and selectors
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")


class WebsiteSession(Base):  # type: ignore[misc]
    """Tracks active browser sessions per website: authentication state,
    cookie consent state, last activity, session expiry."""

    __tablename__ = "website_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    website_knowledge_id = Column(
        UUID(as_uuid=True),
        ForeignKey("website_knowledge.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_token = Column(Text, nullable=False, unique=True, index=True)
    browser_profile = Column(Text, nullable=True)  # chromium, firefox, webkit
    tab_id = Column(Text, nullable=True)
    auth_state = Column(Text, nullable=False, default="unauthenticated")  # unauthenticated, authenticated, expired, challenge_required
    auth_method = Column(Text, nullable=True)  # password, passkey, totp, oauth, saml
    cookie_consent_state = Column(Text, nullable=True)  # accepted, rejected, pending, unknown
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    session_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)


class WebsiteAccountLifecycle(Base):  # type: ignore[misc]
    """Full account lifecycle: registration, verification, activation,
    security configuration, maintenance, suspension, closure."""

    __tablename__ = "website_account_lifecycle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    website_knowledge_id = Column(
        UUID(as_uuid=True),
        ForeignKey("website_knowledge.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_type = Column(Text, nullable=False)  # owned_by_iam, owned_by_creator, authorised_access
    username = Column(Text, nullable=False)
    email = Column(Text, nullable=True)
    registration_date = Column(DateTime(timezone=True), nullable=True)
    verification_status = Column(Text, nullable=False, default="unverified")  # unverified, email_verified, id_verified, phone_verified
    mfa_status = Column(Text, nullable=False, default="none")  # none, totp, hardware_key, sms, email, multi
    recovery_method = Column(Text, nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    account_status = Column(Text, nullable=False, default="active")  # active, suspended, restricted, closed, deleted
    suspension_reason = Column(Text, nullable=True)
    suspension_date = Column(DateTime(timezone=True), nullable=True)
    closure_date = Column(DateTime(timezone=True), nullable=True)
    closure_reason = Column(Text, nullable=True)
    is_owned_by_iam = Column(Boolean, nullable=False, default=False)
    is_owned_by_creator = Column(Boolean, nullable=False, default=False)
    is_authorised_access = Column(Boolean, nullable=False, default=False)
    credentials_stored = Column(Boolean, nullable=False, default=False)
    passkey_registered = Column(Boolean, nullable=False, default=False)
    last_security_check_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("account_status IN ('active', 'suspended', 'restricted', 'closed', 'deleted')",
                        name="ck_account_lifecycle_status"),
    )


class DigitalReputation(Base):  # type: ignore[misc]
    """Digital reputation & trust: account standing, suspensions, ToS changes,
    privacy policy changes, security scores, ownership evidence."""

    __tablename__ = "digital_reputation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    website_knowledge_id = Column(
        UUID(as_uuid=True),
        ForeignKey("website_knowledge.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_username = Column(Text, nullable=False)
    verification_status = Column(Text, nullable=False, default="unverified")  # unverified, verified, disputed
    platform_warnings = Column(JSON, nullable=False, default=list)  # list of warning records
    suspensions = Column(JSON, nullable=False, default=list)  # list of suspension records
    restrictions = Column(JSON, nullable=False, default=list)  # list of restriction records
    tos_changes = Column(JSON, nullable=False, default=list)  # terms-of-service change history
    privacy_changes = Column(JSON, nullable=False, default=list)  # privacy policy change history
    service_reliability_score = Column(Integer, nullable=False, default=50)  # 0-100
    account_security_score = Column(Integer, nullable=False, default=50)  # 0-100
    identity_consistency_score = Column(Integer, nullable=False, default=50)  # 0-100
    ownership_evidence = Column(JSON, nullable=False, default=list)  # ownership proof records
    last_assessed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("service_reliability_score BETWEEN 0 AND 100",
                        name="ck_digital_reputation_service_score"),
        CheckConstraint("account_security_score BETWEEN 0 AND 100",
                        name="ck_digital_reputation_security_score"),
        CheckConstraint("identity_consistency_score BETWEEN 0 AND 100",
                        name="ck_digital_reputation_identity_score"),
    )


class WebsiteConsent(Base):  # type: ignore[misc]
    """Cookie and consent management: per-website cookie categories,
    consent status, last updated, data-retention preferences."""

    __tablename__ = "website_consent"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    website_knowledge_id = Column(
        UUID(as_uuid=True),
        ForeignKey("website_knowledge.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cookie_categories = Column(JSON, nullable=False, default=list)  # essential, analytics, marketing, functional
    consent_status = Column(Text, nullable=False, default="pending")  # pending, accepted, rejected, withdrawn
    consent_date = Column(DateTime(timezone=True), nullable=True)
    data_retention_preference = Column(Text, nullable=True)  # minimize, standard, maximum
    sensitive_info_classification = Column(Text, nullable=True)  # none, low, medium, high, critical
    gdpr_applicable = Column(Boolean, nullable=False, default=False)
    ccpa_applicable = Column(Boolean, nullable=False, default=False)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("consent_status IN ('pending', 'accepted', 'rejected', 'withdrawn')",
                        name="ck_website_consent_status"),
    )


class DigitalSecurityIncident(Base):  # type: ignore[misc]
    """Security incidents: credential leaks, suspicious auth attempts,
    compromised sessions, unauthorised changes, breach monitoring."""

    __tablename__ = "digital_security_incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    website_knowledge_id = Column(
        UUID(as_uuid=True),
        ForeignKey("website_knowledge.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_type = Column(Text, nullable=False)  # credential_leak, suspicious_auth, compromised_session, unauthorised_change, breach
    severity = Column(Text, nullable=False, default="medium")  # low, medium, high, critical
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Text, nullable=False, default="open")  # open, investigating, resolved, closed, false_positive
    affected_accounts = Column(JSON, nullable=False, default=list)
    remediation_actions = Column(JSON, nullable=False, default=list)
    evidence = Column(JSON, nullable=False, default=list)

    __table_args__ = (
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')",
                        name="ck_digital_security_incident_severity"),
        CheckConstraint("status IN ('open', 'investigating', 'resolved', 'closed', 'false_positive')",
                        name="ck_digital_security_incident_status"),
    )


class AutonomousWebTask(Base):  # type: ignore[misc]
    """Autonomous web tasks: multi-step planning, decomposition,
    checkpoints, retry logic, dependency management, scheduled execution,
    progress reporting, cancellation."""

    __tablename__ = "autonomous_web_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    website_knowledge_id = Column(
        UUID(as_uuid=True),
        ForeignKey("website_knowledge.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_type = Column(Text, nullable=False)  # registration, login, data_entry, publication, research, checkout
    status = Column(Text, nullable=False, default="pending")  # pending, planning, executing, paused, completed, failed, cancelled
    priority = Column(Integer, nullable=False, default=5)  # 1-10
    decomposition = Column(JSON, nullable=False, default=list)  # ordered steps
    checkpoints = Column(JSON, nullable=False, default=list)  # completed checkpoint records
    dependencies = Column(JSON, nullable=False, default=list)  # dependent task IDs
    schedule_at = Column(DateTime(timezone=True), nullable=True)  # scheduled execution time
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    progress_percentage = Column(Integer, nullable=False, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=3)
    is_background = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'planning', 'executing', 'paused', 'completed', 'failed', 'cancelled')",
                        name="ck_autonomous_web_task_status"),
        CheckConstraint("priority BETWEEN 1 AND 10",
                        name="ck_autonomous_web_task_priority"),
        CheckConstraint("progress_percentage BETWEEN 0 AND 100",
                        name="ck_autonomous_web_task_progress"),
    )


class BrowserInfrastructure(Base):  # type: ignore[misc]
    """Browser infrastructure: profiles, remote workers, mobile devices,
    health monitoring, resource allocation."""

    __tablename__ = "browser_infrastructure"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    browser_type = Column(Text, nullable=False)  # chromium, firefox, webkit, android_adb, remote_desktop
    mode = Column(Text, nullable=False, default="headless")  # headless, visible
    profile_name = Column(Text, nullable=True)
    remote_endpoint = Column(Text, nullable=True)  # for remote browser execution
    device_serial = Column(Text, nullable=True)  # for mobile ADB devices
    health_status = Column(Text, nullable=False, default="healthy")  # healthy, degraded, offline, unknown
    last_health_check_at = Column(DateTime(timezone=True), nullable=True)
    resource_allocation = Column(JSON, nullable=False, default=dict)  # cpu, memory, concurrent_sessions
    concurrent_session_limit = Column(Integer, nullable=False, default=1)
    active_session_count = Column(Integer, nullable=False, default=0)
    is_available = Column(Boolean, nullable=False, default=True)


class BrowserTaskRun(Base):  # type: ignore[misc]
    """Doc 29 WP-03: browser task execution record with actor attribution.

    A run is linked to an AutonomousWebTask by its external ``task_id`` and
    carries the permission scope, mode and verified state of the browser work.
    """

    __tablename__ = "browser_task_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(Text, nullable=False, index=True)
    session_id = Column(Text, nullable=True, index=True)
    actor = Column(Text, nullable=False)
    actor_type = Column(Text, nullable=False, default="agent")
    permission_scope = Column(Text, nullable=True)
    mode = Column(Text, nullable=False, default="headless")
    engine = Column(Text, nullable=True)
    state = Column(Text, nullable=False, default="queued")
    priority = Column(Integer, nullable=False, default=5)
    deadline = Column(DateTime(timezone=True), nullable=True)
    retries = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    result_ref = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("actor_type IN ('agent','creator')",
                        name="ck_browser_task_run_actor_type"),
        CheckConstraint("mode IN ('headless','visible','isolated')",
                        name="ck_browser_task_run_mode"),
        CheckConstraint(
            "state IN ('queued','running','awaiting_approval','verifying',"
            "'completed','failed','cancelled','timed_out')",
            name="ck_browser_task_run_state"),
    )


class BrowserEvidence(Base):  # type: ignore[misc]
    """Doc 29 WP-03: preserved evidence package for a browser task."""

    __tablename__ = "browser_evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(Text, nullable=False, index=True)
    session_id = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    screenshot_ref = Column(Text, nullable=True)
    excerpt = Column(Text, nullable=True)
    source_metadata = Column(JSON, nullable=False, default=dict)
    sha256 = Column(Text, nullable=False)
    timestamp_ms = Column(BigInteger, nullable=False)
    retention_until = Column(DateTime(timezone=True), nullable=True)


class BrowserAudit(Base):  # type: ignore[misc]
    """Doc 29 WP-03: append-only browser action attribution log.

    No update or delete path is provided by the service; secret values are
    redacted before a row is written.
    """

    __tablename__ = "browser_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(Text, nullable=False, index=True)
    actor = Column(Text, nullable=False)
    actor_type = Column(Text, nullable=False, default="agent")
    action = Column(Text, nullable=False)
    target = Column(Text, nullable=True)
    outcome = Column(JSON, nullable=False, default=dict)
    timestamp_ms = Column(BigInteger, nullable=False)

    __table_args__ = (
        CheckConstraint("actor_type IN ('agent','creator')",
                        name="ck_browser_audit_actor_type"),
    )


class BrowserKnowledgeProposal(Base):  # type: ignore[misc]
    """Doc 29 P4: governed proposal before browser research enters knowledge."""

    __tablename__ = "browser_knowledge_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(Text, nullable=False, index=True)
    claim = Column(Text, nullable=False)
    source_urls = Column(JSON, nullable=False, default=list)
    evidence_refs = Column(JSON, nullable=False, default=list)
    independent_source_count = Column(Integer, nullable=False, default=0)
    verification_state = Column(Text, nullable=False, default="unverified")
    legal_decision = Column(Text, nullable=False, default="BLOCKED")
    status = Column(Text, nullable=False, default="pending_review")
    promotion_ref = Column(Text, nullable=True)
    created_by = Column(Text, nullable=False)
    reviewed_by = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_review','quarantined','approved','rejected')",
            name="ck_browser_knowledge_proposal_status"),
        CheckConstraint(
            "verification_state IN ('unverified','single_source','verified')",
            name="ck_browser_knowledge_proposal_verification"),
    )


class OnionReputation(Base):  # type: ignore[misc]
    """Doc 29 P6: provenance and reputation records for onion services."""

    __tablename__ = "onion_reputation"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address = Column(Text, nullable=False, unique=True, index=True)
    claimed_operator = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="unknown")
    source_urls = Column(JSON, nullable=False, default=list)
    availability = Column(JSON, nullable=False, default=dict)
    assessment = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('unknown','observed','suspicious','confirmed')",
            name="ck_onion_reputation_status"),
    )


class BrowserAgentSession(Base):
    """Doc 29 P7: one isolated browser session per authorised agent."""

    __tablename__ = "browser_agent_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(Text, nullable=False, index=True)
    session_token = Column(Text, nullable=False, unique=True, index=True)
    task_id = Column(Text, nullable=True)
    owner = Column(Text, nullable=False)
    permission_scope = Column(JSON, nullable=False, default=list)
    isolation_level = Column(Text, nullable=False, default="isolated")
    state = Column(Text, nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    payload = Column(JSON, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint(
            "state IN ('open','recovering','closed','released')",
            name="ck_browser_agent_session_state"),
        CheckConstraint(
            "isolation_level IN ('headless','visible','isolated')",
            name="ck_browser_agent_session_isolation"),
    )
