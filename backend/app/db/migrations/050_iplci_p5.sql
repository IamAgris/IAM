-- IP & Legal Intelligence Phase 5 — confirmed OD-48
-- Disputes, incidents, legal holds, deadlines, evidence and continuity.

CREATE TABLE IF NOT EXISTS ip_legal_dispute_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_type TEXT NOT NULL,
    complainant TEXT,
    claim_ref TEXT,
    authority_verified BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'received',
    affected_assets JSONB NOT NULL DEFAULT '[]'::jsonb,
    affected_datasets JSONB NOT NULL DEFAULT '[]'::jsonb,
    affected_models JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    response_ref TEXT,
    deadlines JSONB NOT NULL DEFAULT '[]'::jsonb,
    outcome TEXT,
    case_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_dispute_type CHECK (case_type IN (
        'copyright','trademark','patent','licence','takedown','attribution','ownership')),
    CONSTRAINT ck_ip_legal_dispute_status CHECK (status IN (
        'received','verifying','investigating','restricted','responded',
        'resolved','withdrawn','appealed'))
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_dispute_status ON ip_legal_dispute_cases (status);

CREATE TABLE IF NOT EXISTS ip_legal_incident_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_type TEXT NOT NULL,
    detected_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ,
    affected_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
    affected_projects JSONB NOT NULL DEFAULT '[]'::jsonb,
    affected_models JSONB NOT NULL DEFAULT '[]'::jsonb,
    exposure_assessment TEXT,
    notification_required BOOLEAN NOT NULL DEFAULT FALSE,
    notification_decision TEXT,
    remediation_ref TEXT,
    resolution TEXT,
    rules_updated BOOLEAN NOT NULL DEFAULT FALSE,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ip_legal_legal_holds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reason TEXT NOT NULL,
    case_id UUID,
    scope JSONB NOT NULL DEFAULT '[]'::jsonb,
    issued_by TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    released_at TIMESTAMPTZ,
    released_by TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_legal_holds_case ON ip_legal_legal_holds (case_id);

CREATE TABLE IF NOT EXISTS ip_legal_rights_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    party_id UUID,
    request_type TEXT NOT NULL,
    requested_rights JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'requested',
    agreement_ref TEXT,
    review_date TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_contact_request_type CHECK (request_type IN (
        'permission','licence','renewal','attribution','dataset_permission','training_permission')),
    CONSTRAINT ck_ip_legal_contact_status CHECK (
        status IN ('requested','agreed','rejected','expired','withdrawn'))
);

CREATE TABLE IF NOT EXISTS ip_legal_compliance_deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deadline_type TEXT NOT NULL,
    source_ref TEXT,
    jurisdiction TEXT,
    due_at TIMESTAMPTZ,
    notify_before TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    completed_at TIMESTAMPTZ,
    proof_ref TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_deadline_type CHECK (deadline_type IN (
        'filing','renewal','reporting','retention','dispute','registration','review','deletion'))
);

CREATE TABLE IF NOT EXISTS ip_legal_evidence_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id UUID,
    case_id UUID,
    legal_hold_id UUID,
    source_url TEXT,
    document_ref TEXT,
    legal_provision_ref TEXT,
    licence_version TEXT,
    captured_at TIMESTAMPTZ,
    jurisdiction TEXT,
    content_hash TEXT,
    retention_until TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_evidence_asset ON ip_legal_evidence_records (asset_id);
CREATE INDEX IF NOT EXISTS ix_ip_legal_evidence_case ON ip_legal_evidence_records (case_id);

CREATE TABLE IF NOT EXISTS ip_legal_continuity_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    check_type TEXT NOT NULL DEFAULT 'governance_recovery',
    risk TEXT NOT NULL DEFAULT 'UNKNOWN',
    outcome TEXT NOT NULL,
    problems JSONB NOT NULL DEFAULT '[]'::jsonb,
    recovery_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
