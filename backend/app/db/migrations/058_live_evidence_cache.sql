-- =============================================================================
-- Live evidence cache (proposed Doc 32 §7).
-- Query-level cache with freshness TTL. Source reputation and claim labels are
-- read from the existing iics_sources / iics_claims records; no duplicate
-- reputation store and no new vector database is introduced.
-- =============================================================================

CREATE TABLE IF NOT EXISTS live_evidence_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_hash VARCHAR(64) NOT NULL UNIQUE,
    query TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'unavailable',
    results JSON NOT NULL DEFAULT '[]'::json,
    errors JSON NOT NULL DEFAULT '[]'::json,
    freshness_class TEXT NOT NULL DEFAULT 'current',
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_live_evidence_freshness
        CHECK (freshness_class IN ('breaking', 'current', 'standard', 'stable'))
);

CREATE INDEX IF NOT EXISTS ix_live_evidence_cache_expires_at
    ON live_evidence_cache (expires_at);
