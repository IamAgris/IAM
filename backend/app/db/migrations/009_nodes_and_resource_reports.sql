-- =============================================================================
-- Node registry and bounded resource reports (OD-26, OD-29)
-- =============================================================================
-- Nodes are candidates, never trusted peers. contribution_percent is a ceiling
-- of operator-permitted resources expressed as a percentage (1.0 = 1%).

CREATE TABLE IF NOT EXISTS registered_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    architecture TEXT NOT NULL,
    resources JSONB NOT NULL DEFAULT '{}'::jsonb,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    trust_level TEXT NOT NULL DEFAULT 'candidate',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    contribution_percent DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    status TEXT NOT NULL DEFAULT 'registered',
    registered_by_token_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ,
    CONSTRAINT ck_registered_node_trust_level
        CHECK (trust_level IN ('candidate', 'restricted', 'trusted', 'revoked')),
    CONSTRAINT ck_registered_node_contribution_ceiling
        CHECK (contribution_percent >= 0 AND contribution_percent <= 1)
);

CREATE TABLE IF NOT EXISTS node_resource_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES registered_nodes(id) ON DELETE CASCADE,
    cpu_cores INTEGER NOT NULL,
    ram_bytes DOUBLE PRECISION NOT NULL,
    storage_bytes DOUBLE PRECISION NOT NULL,
    used_percent DOUBLE PRECISION,
    contribution_percent DOUBLE PRECISION NOT NULL,
    permitted_ram_bytes DOUBLE PRECISION NOT NULL,
    permitted_storage_bytes DOUBLE PRECISION NOT NULL,
    reported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_node_resource_reports_node_id
    ON node_resource_reports (node_id);
CREATE INDEX IF NOT EXISTS ix_node_resource_reports_reported_at
    ON node_resource_reports (reported_at DESC);
