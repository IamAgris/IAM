-- =============================================================================
-- IICS foundation overlay (pending proposal — IAM_IICS_GAP_CLOSURE_ADDENDUM.md)
-- Egress/source rights, claim evidence, action ledger and benchmark results.
-- No new top-level system, no new queue (OD-08 ARQ is reused).
-- =============================================================================

CREATE TABLE IF NOT EXISTS iics_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    source_type TEXT NOT NULL DEFAULT 'public_web',
    licence TEXT,
    rights JSON NOT NULL DEFAULT '{}'::json,
    territory TEXT,
    freshness_class TEXT NOT NULL DEFAULT 'documentation',
    reliability_score NUMERIC(5, 4) NOT NULL DEFAULT 0,
    conditions JSON NOT NULL DEFAULT '[]'::json,
    legal_audit_event_id TEXT,
    last_checked_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_iics_source_type
        CHECK (source_type IN ('public_web', 'api', 'document', 'feed')),
    CONSTRAINT ck_iics_freshness_class
        CHECK (freshness_class IN ('volatile', 'documentation', 'standard', 'stable'))
);

CREATE INDEX IF NOT EXISTS ix_iics_sources_domain ON iics_sources (domain);
CREATE INDEX IF NOT EXISTS ix_iics_sources_expires_at ON iics_sources (expires_at);

CREATE TABLE IF NOT EXISTS iics_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES iics_sources(id) ON DELETE CASCADE,
    claim TEXT NOT NULL,
    locator TEXT,
    publication_date TEXT,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    confidence NUMERIC(5, 4) NOT NULL DEFAULT 0,
    label TEXT NOT NULL DEFAULT 'unverified',
    CONSTRAINT ck_iics_claim_label
        CHECK (label IN ('verified', 'provisional', 'unverified',
                         'outdated', 'contradicted', 'unresolved'))
);

CREATE INDEX IF NOT EXISTS ix_iics_claims_source_id ON iics_claims (source_id);

CREATE TABLE IF NOT EXISTS iics_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor TEXT NOT NULL,
    tool TEXT NOT NULL,
    target TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'public',
    permission_source TEXT NOT NULL DEFAULT 'legal_gateway',
    approval_ref TEXT,
    idempotency_key VARCHAR(128) NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'planned',
    verification_result JSON NOT NULL DEFAULT '{}'::json,
    bytes_transferred INTEGER NOT NULL DEFAULT 0,
    cost_units INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_iics_action_scope
        CHECK (scope IN ('public', 'authenticated', 'financial', 'protected_core')),
    CONSTRAINT ck_iics_action_status
        CHECK (status IN ('planned', 'executing', 'verified', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS ix_iics_actions_idempotency_key
    ON iics_actions (idempotency_key);
CREATE INDEX IF NOT EXISTS ix_iics_actions_created_at ON iics_actions (created_at);

CREATE TABLE IF NOT EXISTS iics_benchmark_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    benchmark TEXT NOT NULL,
    score NUMERIC(5, 4) NOT NULL,
    threshold NUMERIC(5, 4) NOT NULL,
    passed BOOLEAN NOT NULL,
    evidence JSON NOT NULL DEFAULT '{}'::json,
    run_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_iics_benchmark_results_benchmark
    ON iics_benchmark_results (benchmark);
