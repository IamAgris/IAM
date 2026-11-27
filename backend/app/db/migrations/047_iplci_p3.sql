-- IP & Legal Intelligence Phase 3 — proposed OD-48
-- Collection legality, privacy/data protection and AI-training governance.

CREATE TABLE IF NOT EXISTS ip_legal_collection_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_uri TEXT NOT NULL,
    intended_use TEXT NOT NULL DEFAULT 'research',
    risk TEXT NOT NULL DEFAULT 'UNKNOWN',
    outcome TEXT NOT NULL,
    blocked BOOLEAN NOT NULL DEFAULT FALSE,
    flags JSONB NOT NULL DEFAULT '{}'::jsonb,
    conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    policy_version TEXT NOT NULL DEFAULT '3.0',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ip_legal_privacy_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID,
    jurisdiction TEXT NOT NULL DEFAULT 'ZA',
    personal_data_present BOOLEAN NOT NULL DEFAULT FALSE,
    data_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
    lawful_basis TEXT,
    explicit_consent BOOLEAN NOT NULL DEFAULT FALSE,
    dpia_completed BOOLEAN NOT NULL DEFAULT FALSE,
    minimisation_applied BOOLEAN NOT NULL DEFAULT FALSE,
    retention_period TEXT,
    deletion_supported BOOLEAN NOT NULL DEFAULT FALSE,
    deletion_requested BOOLEAN NOT NULL DEFAULT FALSE,
    deletion_completed BOOLEAN NOT NULL DEFAULT FALSE,
    dsar_requested BOOLEAN NOT NULL DEFAULT FALSE,
    dsar_completed BOOLEAN NOT NULL DEFAULT FALSE,
    international_transfer BOOLEAN NOT NULL DEFAULT FALSE,
    transfer_mechanism TEXT,
    disclosure_permitted BOOLEAN NOT NULL DEFAULT FALSE,
    risk TEXT NOT NULL DEFAULT 'UNKNOWN',
    outcome TEXT NOT NULL DEFAULT 'quarantined',
    verification_status TEXT NOT NULL DEFAULT 'requires_verification',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_privacy_source ON ip_legal_privacy_records (source_id);

CREATE TABLE IF NOT EXISTS ip_legal_training_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID,
    dataset_id UUID,
    requester TEXT NOT NULL DEFAULT 'main',
    approver TEXT NOT NULL,
    ingestion_reviewer TEXT NOT NULL,
    decision TEXT NOT NULL DEFAULT 'pending',
    basis TEXT,
    purpose TEXT,
    expires_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_training_approval_decision CHECK (
        decision IN ('pending','approved','rejected','revoked'))
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_training_approval_dataset ON ip_legal_training_approvals (dataset_id);

CREATE TABLE IF NOT EXISTS ip_legal_model_lineages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id TEXT NOT NULL,
    base_model TEXT NOT NULL,
    base_model_version TEXT,
    base_model_licence TEXT,
    dataset_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    approval_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    training_date TIMESTAMPTZ,
    evaluation_ref TEXT,
    promotion_status TEXT NOT NULL DEFAULT 'candidate',
    affected_by_revocation JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_model_lineage_model ON ip_legal_model_lineages (model_id);
