-- IAM Browser Substrate — Doc 29 WP-03 (OD-49)
-- Task attribution, evidence packages and append-only browser audit.
-- Does not replace any existing web/UWAIE table.

CREATE TABLE IF NOT EXISTS browser_task_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT NOT NULL,
    session_id TEXT,
    actor TEXT NOT NULL,
    actor_type TEXT NOT NULL DEFAULT 'agent',
    permission_scope TEXT,
    mode TEXT NOT NULL DEFAULT 'headless',
    engine TEXT,
    state TEXT NOT NULL DEFAULT 'queued',
    priority INTEGER NOT NULL DEFAULT 5,
    deadline TIMESTAMPTZ,
    retries INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    result_ref TEXT,
    CONSTRAINT ck_browser_task_run_actor_type CHECK (actor_type IN ('agent','creator')),
    CONSTRAINT ck_browser_task_run_mode CHECK (mode IN ('headless','visible','isolated')),
    CONSTRAINT ck_browser_task_run_state CHECK (state IN (
        'queued','running','awaiting_approval','verifying',
        'completed','failed','cancelled','timed_out'))
);
CREATE INDEX IF NOT EXISTS ix_browser_task_runs_task_id ON browser_task_runs (task_id);
CREATE INDEX IF NOT EXISTS ix_browser_task_runs_session_id ON browser_task_runs (session_id);

CREATE TABLE IF NOT EXISTS browser_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT NOT NULL,
    session_id TEXT,
    url TEXT,
    screenshot_ref TEXT,
    excerpt TEXT,
    source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    sha256 TEXT NOT NULL,
    timestamp_ms BIGINT NOT NULL,
    retention_until TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_browser_evidence_task_id ON browser_evidence (task_id);

CREATE TABLE IF NOT EXISTS browser_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    actor_type TEXT NOT NULL DEFAULT 'agent',
    action TEXT NOT NULL,
    target TEXT,
    outcome JSONB NOT NULL DEFAULT '{}'::jsonb,
    timestamp_ms BIGINT NOT NULL,
    CONSTRAINT ck_browser_audit_actor_type CHECK (actor_type IN ('agent','creator'))
);
CREATE INDEX IF NOT EXISTS ix_browser_audit_task_id ON browser_audit (task_id);
