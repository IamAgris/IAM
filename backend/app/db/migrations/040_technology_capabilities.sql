-- Doc 20 / OD-36: third-party technology registry (distinct from model and
-- IAM capability registries). No code is installed or executed by this table.

CREATE TABLE IF NOT EXISTS technology_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    version TEXT,
    official_source TEXT,
    source_url TEXT,
    language TEXT,
    architectures JSONB NOT NULL DEFAULT '[]'::jsonb,
    licence TEXT,
    commercial_use_ok BOOLEAN NOT NULL DEFAULT FALSE,
    cost_status TEXT NOT NULL DEFAULT 'free',
    hardware_requirements JSONB NOT NULL DEFAULT '{}'::jsonb,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    limitations JSONB NOT NULL DEFAULT '[]'::jsonb,
    security_status TEXT,
    maintenance_status TEXT,
    compatibility JSONB NOT NULL DEFAULT '{}'::jsonb,
    test_results JSONB NOT NULL DEFAULT '[]'::jsonb,
    benchmarks JSONB NOT NULL DEFAULT '[]'::jsonb,
    lifecycle_state TEXT NOT NULL DEFAULT 'researched',
    notes TEXT,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_reviewed_at TIMESTAMPTZ,
    CONSTRAINT ck_tech_cost_status CHECK (cost_status IN ('free', 'open_source', 'paid', 'mixed')),
    CONSTRAINT ck_tech_lifecycle_state CHECK (
        lifecycle_state IN ('researched', 'tested', 'approved', 'integrated', 'deprecated', 'rejected')
    )
);
CREATE INDEX IF NOT EXISTS ix_tech_capabilities_name ON technology_capabilities (name);
CREATE INDEX IF NOT EXISTS ix_tech_capabilities_lifecycle ON technology_capabilities (lifecycle_state);
