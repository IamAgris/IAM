-- =============================================================================
-- Skill Runtime captured logs
-- =============================================================================

CREATE TABLE IF NOT EXISTS skill_runtime_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES skill_runtime_executions(id) ON DELETE CASCADE,
    stream TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS ix_skill_runtime_logs_execution
    ON skill_runtime_logs (execution_id);
