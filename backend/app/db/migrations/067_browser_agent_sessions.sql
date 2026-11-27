-- IAM multi-agent browser sessions — Doc 29 P7 (OD-49)
-- One session per agent; sharing requires signed Creator approval.

CREATE TABLE IF NOT EXISTS browser_agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    session_token TEXT NOT NULL UNIQUE,
    task_id TEXT,
    owner TEXT NOT NULL,
    permission_scope JSONB NOT NULL DEFAULT '[]'::jsonb,
    isolation_level TEXT NOT NULL DEFAULT 'isolated',
    state TEXT NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT ck_browser_agent_session_state CHECK (
        state IN ('open','recovering','closed','released')),
    CONSTRAINT ck_browser_agent_session_isolation CHECK (
        isolation_level IN ('headless','visible','isolated'))
);
CREATE INDEX IF NOT EXISTS ix_browser_agent_sessions_agent_id
    ON browser_agent_sessions (agent_id);
CREATE INDEX IF NOT EXISTS ix_browser_agent_sessions_state
    ON browser_agent_sessions (state);
