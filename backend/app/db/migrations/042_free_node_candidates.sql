-- Doc 19 / OD-35: free infrastructure node candidates and lifecycle.
-- Assessment records only; no credentials or cloud accounts are created here.

CREATE TABLE IF NOT EXISTS free_node_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    instance_class TEXT,
    architecture TEXT NOT NULL,
    region TEXT,
    cpu_cores NUMERIC(4, 2) NOT NULL DEFAULT 0,
    ram_mb INTEGER NOT NULL DEFAULT 0,
    disk_gb NUMERIC(6, 2) NOT NULL DEFAULT 0,
    cost_status TEXT NOT NULL DEFAULT 'free',
    terms_source TEXT,
    eligibility_verified BOOLEAN NOT NULL DEFAULT FALSE,
    useful BOOLEAN NOT NULL DEFAULT FALSE,
    usefulness_reason TEXT,
    run_compatible BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'discovered',
    authorisation_required BOOLEAN NOT NULL DEFAULT TRUE,
    registered_node_id TEXT,
    expires_at TIMESTAMPTZ,
    quota_alarm_at TIMESTAMPTZ,
    migration_plan TEXT,
    notes TEXT,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_reviewed_at TIMESTAMPTZ,
    CONSTRAINT ck_freenode_arch CHECK (architecture IN ('amd64', 'arm64')),
    CONSTRAINT ck_freenode_cost_status CHECK (cost_status IN ('free', 'free_credit', 'unknown')),
    CONSTRAINT ck_freenode_status CHECK (
        status IN ('discovered', 'assessed', 'authorised', 'deployed', 'registered',
                   'expiring', 'migrated', 'stopped', 'rejected')
    )
);
CREATE INDEX IF NOT EXISTS ix_freenode_provider ON free_node_candidates (provider);
CREATE INDEX IF NOT EXISTS ix_freenode_status ON free_node_candidates (status);
