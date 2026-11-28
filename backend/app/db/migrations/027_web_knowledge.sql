-- =============================================================================
# Website Knowledge Base & Universal Web Interaction System (Phase 10)
# =============================================================================

-- Website knowledge base: per-website learned knowledge
CREATE TABLE IF NOT EXISTS website_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL UNIQUE,
    display_name TEXT,
    homepage_url TEXT,
    login_procedure JSON NOT NULL DEFAULT '[]'::json,
    auth_methods JSON NOT NULL DEFAULT '[]'::json,
    registration_procedure JSON NOT NULL DEFAULT '[]'::json,
    supported_passkeys BOOLEAN NOT NULL DEFAULT false,
    mfa_methods JSON NOT NULL DEFAULT '[]'::json,
    known_restrictions JSON NOT NULL DEFAULT '[]'::json,
    browser_compatibility JSON NOT NULL DEFAULT '[]'::json,
    verification_requirements JSON NOT NULL DEFAULT '[]'::json,
    prior_failures JSON NOT NULL DEFAULT '[]'::json,
    success_patterns JSON NOT NULL DEFAULT '[]'::json,
    last_verified_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- Website sessions: per-website browser session tracking
CREATE TABLE IF NOT EXISTS website_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_knowledge_id UUID NOT NULL REFERENCES website_knowledge(id) ON DELETE CASCADE,
    session_token TEXT NOT NULL UNIQUE,
    browser_profile TEXT,
    tab_id TEXT,
    auth_state TEXT NOT NULL DEFAULT 'unauthenticated',
    auth_method TEXT,
    cookie_consent_state TEXT,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    session_expires_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- Website account lifecycle: full account lifecycle management
CREATE TABLE IF NOT EXISTS website_account_lifecycle (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_knowledge_id UUID NOT NULL REFERENCES website_knowledge(id) ON DELETE CASCADE,
    account_type TEXT NOT NULL,
    username TEXT NOT NULL,
    email TEXT,
    registration_date TIMESTAMPTZ,
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    mfa_status TEXT NOT NULL DEFAULT 'none',
    recovery_method TEXT,
    last_login_at TIMESTAMPTZ,
    account_status TEXT NOT NULL DEFAULT 'active',
    suspension_reason TEXT,
    suspension_date TIMESTAMPTZ,
    closure_date TIMESTAMPTZ,
    closure_reason TEXT,
    is_owned_by_iam BOOLEAN NOT NULL DEFAULT false,
    is_owned_by_creator BOOLEAN NOT NULL DEFAULT false,
    is_authorised_access BOOLEAN NOT NULL DEFAULT false,
    credentials_stored BOOLEAN NOT NULL DEFAULT false,
    passkey_registered BOOLEAN NOT NULL DEFAULT false,
    last_security_check_at TIMESTAMPTZ
);

-- Digital reputation & trust
CREATE TABLE IF NOT EXISTS digital_reputation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_knowledge_id UUID NOT NULL REFERENCES website_knowledge(id) ON DELETE CASCADE,
    account_username TEXT NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    platform_warnings JSON NOT NULL DEFAULT '[]'::json,
    suspensions JSON NOT NULL DEFAULT '[]'::json,
    restrictions JSON NOT NULL DEFAULT '[]'::json,
    tos_changes JSON NOT NULL DEFAULT '[]'::json,
    privacy_changes JSON NOT NULL DEFAULT '[]'::json,
    service_reliability_score INTEGER NOT NULL DEFAULT 50,
    account_security_score INTEGER NOT NULL DEFAULT 50,
    identity_consistency_score INTEGER NOT NULL DEFAULT 50,
    ownership_evidence JSON NOT NULL DEFAULT '[]'::json,
    last_assessed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Website consent management: cookie and consent preferences
CREATE TABLE IF NOT EXISTS website_consent (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_knowledge_id UUID NOT NULL REFERENCES website_knowledge(id) ON DELETE CASCADE,
    cookie_categories JSON NOT NULL DEFAULT '[]'::json,
    consent_status TEXT NOT NULL DEFAULT 'pending',
    consent_date TIMESTAMPTZ,
    data_retention_preference TEXT,
    sensitive_info_classification TEXT,
    gdpr_applicable BOOLEAN NOT NULL DEFAULT false,
    ccpa_applicable BOOLEAN NOT NULL DEFAULT false,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Digital security incidents
CREATE TABLE IF NOT EXISTS digital_security_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_knowledge_id UUID NOT NULL REFERENCES website_knowledge(id) ON DELETE CASCADE,
    incident_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'medium',
    title TEXT NOT NULL,
    description TEXT,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'open',
    affected_accounts JSON NOT NULL DEFAULT '[]'::json,
    remediation_actions JSON NOT NULL DEFAULT '[]'::json,
    evidence JSON NOT NULL DEFAULT '[]'::json
);

-- Autonomous web tasks
CREATE TABLE IF NOT EXISTS autonomous_web_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    website_knowledge_id UUID REFERENCES website_knowledge(id) ON DELETE SET NULL,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    priority INTEGER NOT NULL DEFAULT 5,
    decomposition JSON NOT NULL DEFAULT '[]'::json,
    checkpoints JSON NOT NULL DEFAULT '[]'::json,
    dependencies JSON NOT NULL DEFAULT '[]'::json,
    schedule_at TIMESTAMPTZ,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    progress_percentage INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    is_background BOOLEAN NOT NULL DEFAULT false
);

-- Browser infrastructure
CREATE TABLE IF NOT EXISTS browser_infrastructure (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    browser_type TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'headless',
    profile_name TEXT,
    remote_endpoint TEXT,
    device_serial TEXT,
    health_status TEXT NOT NULL DEFAULT 'healthy',
    last_health_check_at TIMESTAMPTZ,
    resource_allocation JSON NOT NULL DEFAULT '{}'::json,
    concurrent_session_limit INTEGER NOT NULL DEFAULT 1,
    active_session_count INTEGER NOT NULL DEFAULT 0,
    is_available BOOLEAN NOT NULL DEFAULT true
);

-- Check constraints
ALTER TABLE website_sessions
    ADD CONSTRAINT ck_website_session_auth_state
        CHECK (auth_state IN ('unauthenticated', 'authenticated', 'expired', 'challenge_required'));

ALTER TABLE website_sessions
    ADD CONSTRAINT ck_website_session_cookie_consent
        CHECK (cookie_consent_state IS NULL OR cookie_consent_state IN ('accepted', 'rejected', 'pending', 'unknown'));

ALTER TABLE website_account_lifecycle
    ADD CONSTRAINT ck_website_account_lifecycle_status
        CHECK (account_status IN ('active', 'suspended', 'restricted', 'closed', 'deleted'));

ALTER TABLE website_account_lifecycle
    ADD CONSTRAINT ck_website_account_lifecycle_verification
        CHECK (verification_status IN ('unverified', 'email_verified', 'id_verified', 'phone_verified'));

ALTER TABLE website_account_lifecycle
    ADD CONSTRAINT ck_website_account_lifecycle_mfa
        CHECK (mfa_status IN ('none', 'totp', 'hardware_key', 'sms', 'email', 'multi'));

ALTER TABLE digital_reputation
    ADD CONSTRAINT ck_digital_reputation_service_score
        CHECK (service_reliability_score BETWEEN 0 AND 100);

ALTER TABLE digital_reputation
    ADD CONSTRAINT ck_digital_reputation_security_score
        CHECK (account_security_score BETWEEN 0 AND 100);

ALTER TABLE digital_reputation
    ADD CONSTRAINT ck_digital_reputation_identity_score
        CHECK (identity_consistency_score BETWEEN 0 AND 100);

ALTER TABLE website_consent
    ADD CONSTRAINT ck_website_consent_status
        CHECK (consent_status IN ('pending', 'accepted', 'rejected', 'withdrawn'));

ALTER TABLE digital_security_incidents
    ADD CONSTRAINT ck_digital_security_incident_severity
        CHECK (severity IN ('low', 'medium', 'high', 'critical'));

ALTER TABLE digital_security_incidents
    ADD CONSTRAINT ck_digital_security_incident_status
        CHECK (status IN ('open', 'investigating', 'resolved', 'closed', 'false_positive'));

ALTER TABLE autonomous_web_tasks
    ADD CONSTRAINT ck_autonomous_web_task_status
        CHECK (status IN ('pending', 'planning', 'executing', 'paused', 'completed', 'failed', 'cancelled'));

ALTER TABLE autonomous_web_tasks
    ADD CONSTRAINT ck_autonomous_web_task_priority
        CHECK (priority BETWEEN 1 AND 10);

ALTER TABLE autonomous_web_tasks
    ADD CONSTRAINT ck_autonomous_web_task_progress
        CHECK (progress_percentage BETWEEN 0 AND 100);

ALTER TABLE browser_infrastructure
    ADD CONSTRAINT ck_browser_infrastructure_health
        CHECK (health_status IN ('healthy', 'degraded', 'offline', 'unknown'));
