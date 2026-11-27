-- IP & Legal Intelligence (IPLCI) Phase 1 — proposed OD-48
-- Rights assessment, permissions, ownership, provenance and append-only audit.
-- Distinct from the OD-31 legal-intelligence tables (037) and the owned-asset
-- tables (ip_records / asset_licences).

CREATE TABLE IF NOT EXISTS ip_legal_parties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    party_type TEXT NOT NULL DEFAULT 'third_party',
    contact_ref TEXT,
    authority_evidence TEXT,
    verified_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_party_type CHECK (
        party_type IN ('person','entity','creator','iam','third_party'))
);

CREATE TABLE IF NOT EXISTS ip_legal_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    uri TEXT NOT NULL,
    title TEXT,
    description TEXT,
    owner_id UUID,
    author TEXT,
    publisher TEXT,
    acquisition_method TEXT NOT NULL DEFAULT 'other',
    collection_method TEXT,
    collected_at TIMESTAMPTZ,
    rights_status TEXT NOT NULL DEFAULT 'UNKNOWN_OWNERSHIP',
    source_class TEXT NOT NULL DEFAULT 'UNVERIFIED',
    jurisdiction TEXT,
    permission_evidence TEXT,
    licence_id UUID,
    expiry_date TIMESTAMPTZ,
    revocation_conditions TEXT,
    permission_withdrawn BOOLEAN NOT NULL DEFAULT FALSE,
    territory JSONB,
    personal_data_present BOOLEAN NOT NULL DEFAULT FALSE,
    privacy_lawful_basis TEXT,
    attribution_required BOOLEAN NOT NULL DEFAULT FALSE,
    licence_flags JSONB NOT NULL DEFAULT '{}'::jsonb,
    current_permission_state TEXT NOT NULL DEFAULT 'NOT_VALIDATED',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_source_rights CHECK (rights_status IN (
        'PUBLIC_DOMAIN','OPEN_LICENCE','CREATIVE_COMMONS',
        'COMMERCIAL_LICENCE','COPYRIGHT_PROTECTED','UNKNOWN_OWNERSHIP')),
    CONSTRAINT ck_ip_legal_source_class CHECK (source_class IN (
        'OPEN_RESEARCH','REFERENCE_ONLY','LICENSED_RESEARCH',
        'RESTRICTED_RESEARCH','CONFIDENTIAL','UNVERIFIED','PROHIBITED')),
    CONSTRAINT ck_ip_legal_source_state CHECK (current_permission_state IN (
        'NOT_VALIDATED','APPROVED','RESTRICTED',
        'QUARANTINED','REVOKED','EXPIRED','BLOCKED'))
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_sources_state ON ip_legal_sources (current_permission_state);

CREATE TABLE IF NOT EXISTS ip_legal_licences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    identifier TEXT NOT NULL,
    version TEXT,
    licence_text_ref TEXT,
    commercial_use BOOLEAN,
    modification BOOLEAN,
    redistribution BOOLEAN,
    attribution_required BOOLEAN NOT NULL DEFAULT FALSE,
    share_alike BOOLEAN NOT NULL DEFAULT FALSE,
    non_commercial BOOLEAN NOT NULL DEFAULT FALSE,
    territory JSONB,
    effective_from TIMESTAMPTZ,
    effective_to TIMESTAMPTZ,
    verified_by TEXT,
    verified_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ip_legal_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL,
    "right" TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'UNKNOWN',
    basis TEXT,
    conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_ref TEXT,
    assessed_by TEXT,
    assessed_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_permission_right CHECK ("right" IN (
        'read','analyse','store','reproduce','derive','modify',
        'distribute','train','commercialise','disclose')),
    CONSTRAINT ck_ip_legal_permission_state CHECK (state IN ('PERMITTED','PROHIBITED','UNKNOWN'))
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_permissions_source ON ip_legal_permissions (source_id);

CREATE TABLE IF NOT EXISTS ip_legal_assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID,
    operation TEXT NOT NULL,
    agent_id TEXT NOT NULL DEFAULT 'main',
    decision TEXT NOT NULL DEFAULT 'QUARANTINED',
    decision_class TEXT NOT NULL DEFAULT 'UNKNOWN',
    jurisdiction TEXT,
    reason TEXT,
    rules_applied JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    rights_evaluated JSONB NOT NULL DEFAULT '{}'::jsonb,
    conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_version TEXT NOT NULL DEFAULT '1.0',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_assessment_decision CHECK (decision IN (
        'APPROVED','CONDITIONAL','BLOCKED','QUARANTINED','REVOKED','EXPIRED')),
    CONSTRAINT ck_ip_legal_assessment_class CHECK (decision_class IN (
        'LOW','MODERATE','HIGH','CRITICAL','UNKNOWN'))
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_assessments_source ON ip_legal_assessments (source_id);

CREATE TABLE IF NOT EXISTS ip_legal_ip_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_type TEXT NOT NULL,
    title TEXT NOT NULL,
    created_by TEXT,
    legal_owner TEXT NOT NULL,
    origin TEXT NOT NULL DEFAULT 'iam',
    inventorship JSONB,
    transfer_reference TEXT,
    third_party_contributions JSONB NOT NULL DEFAULT '[]'::jsonb,
    ownership_status TEXT NOT NULL DEFAULT 'unknown',
    registration_status TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_asset_origin CHECK (origin IN ('iam','creator','third_party','joint')),
    CONSTRAINT ck_ip_legal_asset_ownership CHECK (
        ownership_status IN ('owned','licensed','disputed','unknown'))
);

CREATE TABLE IF NOT EXISTS ip_legal_dataset_provenance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dataset_version TEXT NOT NULL,
    source_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    assessment_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    collection_history TEXT,
    privacy_classification TEXT NOT NULL DEFAULT 'unknown',
    permitted_purposes JSONB NOT NULL DEFAULT '[]'::jsonb,
    retention_policy TEXT,
    approval_status TEXT NOT NULL DEFAULT 'pending',
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_dataset_approval CHECK (
        approval_status IN ('pending','approved','rejected','revoked'))
);

CREATE TABLE IF NOT EXISTS ip_legal_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence INTEGER NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'sdk',
    resource_id TEXT,
    decision TEXT,
    policy_version TEXT NOT NULL DEFAULT '1.0',
    ruleset_version TEXT NOT NULL DEFAULT '1.0',
    previous_hash TEXT NOT NULL,
    event_hash TEXT NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_audit_hash ON ip_legal_audit_events (event_hash);
CREATE INDEX IF NOT EXISTS ix_ip_legal_audit_sequence ON ip_legal_audit_events (sequence);
