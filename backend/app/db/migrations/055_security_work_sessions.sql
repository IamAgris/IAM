-- =============================================================================
-- Disposable security labs and remediation validation (WH-04/WH-05)
-- =============================================================================

CREATE TABLE IF NOT EXISTS security_work_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    kind TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    target TEXT NOT NULL,
    workspace_id UUID REFERENCES workspace_environments(id) ON DELETE SET NULL,
    authorization_id UUID REFERENCES creator_authorizations(id) ON DELETE SET NULL,
    details JSON NOT NULL DEFAULT '{}'::json,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    CONSTRAINT ck_security_session_kind
        CHECK (kind IN ('simulation_lab', 'remediation_validation')),
    CONSTRAINT ck_security_session_status
        CHECK (status IN ('created', 'running', 'verified', 'failed', 'destroyed', 'expired'))
);

CREATE INDEX IF NOT EXISTS ix_security_work_sessions_target
    ON security_work_sessions (target);
