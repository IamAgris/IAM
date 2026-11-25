-- =============================================================================
-- Skill Runtime execution audit
-- =============================================================================
-- The runtime is disabled by default and only invokes skills after an
-- independent effective-permissions check. Every invocation is recorded.

CREATE TABLE IF NOT EXISTS skill_runtime_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id TEXT NOT NULL,
    permission TEXT NOT NULL,
    script TEXT,
    caller TEXT NOT NULL DEFAULT 'iam',
    adapter TEXT NOT NULL DEFAULT 'stub',
    status TEXT NOT NULL DEFAULT 'completed',
    dry_run BOOLEAN NOT NULL DEFAULT TRUE,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT ck_skill_runtime_status CHECK (
        status IN ('completed', 'denied', 'failed')
    )
);

CREATE INDEX IF NOT EXISTS ix_skill_runtime_skill_id
    ON skill_runtime_executions (skill_id);
