-- =============================================================================
-- Workspace manager (WS-01/WS-02) — isolated, replaceable dev environments
-- =============================================================================

CREATE TABLE IF NOT EXISTS workspace_environments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    project_id UUID,
    provider TEXT NOT NULL DEFAULT 'local',
    status TEXT NOT NULL DEFAULT 'provisioning',
    isolation JSON NOT NULL DEFAULT '{}'::json,
    credential_env_var TEXT,
    directory TEXT NOT NULL,
    last_output TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_workspace_status
        CHECK (status IN ('provisioning', 'active', 'saved', 'destroyed', 'failed'))
);

CREATE INDEX IF NOT EXISTS ix_workspace_environments_project
    ON workspace_environments (project_id);
