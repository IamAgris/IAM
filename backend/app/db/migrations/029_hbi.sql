-- =============================================================================
-- Document 26 (OD-45): HBI Phase 1 persistent memory
-- =============================================================================

CREATE TABLE IF NOT EXISTS hbi_knowledge_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    record_ref TEXT NOT NULL UNIQUE,
    claim TEXT NOT NULL,
    epistemic_type TEXT NOT NULL CHECK (epistemic_type IN ('observation','interpretation','hypothesis','prediction')),
    evidence_class TEXT NOT NULL DEFAULT 'unverified' CHECK (evidence_class IN ('verified','well_supported','contested','unverified','speculation')),
    scope TEXT NOT NULL DEFAULT 'aggregate' CHECK (scope IN ('aggregate','individual')),
    tier TEXT NOT NULL DEFAULT 'T0' CHECK (tier IN ('T0','T1','T2','T3')),
    population TEXT,
    context_dimensions JSON NOT NULL DEFAULT '{}'::json,
    evidence JSON NOT NULL DEFAULT '[]'::json,
    confidence NUMERIC(3,2) NOT NULL DEFAULT 0 CHECK (confidence BETWEEN 0 AND 1),
    uncertainty JSON NOT NULL DEFAULT '{}'::json,
    alternatives JSON NOT NULL DEFAULT '[]'::json,
    falsifier TEXT,
    causal_status TEXT NOT NULL DEFAULT 'correlational' CHECK (causal_status IN ('causal','correlational','speculative')),
    module_ids JSON NOT NULL DEFAULT '[]'::json,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hbi_records_scope_tier ON hbi_knowledge_records(scope, tier);
CREATE INDEX IF NOT EXISTS idx_hbi_records_type ON hbi_knowledge_records(epistemic_type);

CREATE TABLE IF NOT EXISTS hbi_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    purpose TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('aggregate','individual')),
    outcome TEXT NOT NULL,
    detail JSON NOT NULL DEFAULT '{}'::json,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hbi_audit_created ON hbi_audit_events(created_at DESC);
