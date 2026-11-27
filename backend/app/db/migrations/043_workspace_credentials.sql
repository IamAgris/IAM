-- =============================================================================
-- Per-workspace scoped credentials (WS-03) — names and scopes only, no values
-- =============================================================================

CREATE TABLE IF NOT EXISTS workspace_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspace_environments(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    secret_env_var TEXT NOT NULL,
    scopes JSON NOT NULL DEFAULT '{}'::json,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT ck_workspace_credential_purpose
        CHECK (purpose IN ('git', 'package_registry', 'api', 'test_fixture'))
);

CREATE INDEX IF NOT EXISTS ix_workspace_credentials_workspace
    ON workspace_credentials (workspace_id);
