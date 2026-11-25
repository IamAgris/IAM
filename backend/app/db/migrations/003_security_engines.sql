-- =============================================================================
-- IAM Cybersecurity — External Security Engines (ARTEX integration)
-- =============================================================================
-- ARTEX is optional, replaceable and isolated from the protected core.
-- Apply after 002_skillforge.sql.

CREATE TABLE IF NOT EXISTS security_engines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL DEFAULT 'artex',
    transport TEXT NOT NULL DEFAULT 'mcp_streamable_http',
    base_url TEXT NOT NULL,
    token_env_var TEXT NOT NULL DEFAULT 'ARTEX_MCP_TOKEN',
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    dry_run BOOLEAN NOT NULL DEFAULT TRUE,
    allow_private_network BOOLEAN NOT NULL DEFAULT FALSE,
    allow_execution BOOLEAN NOT NULL DEFAULT FALSE,
    allowed_scopes JSONB NOT NULL DEFAULT '["read"]'::jsonb,
    created_by TEXT NOT NULL DEFAULT 'owner',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_security_engine_provider CHECK (provider IN ('artex', 'generic')),
    CONSTRAINT ck_security_engine_transport CHECK (
        transport IN ('mcp_streamable_http', 'http_api', 'stub')
    )
);

CREATE TABLE IF NOT EXISTS security_engine_scopes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engine_id UUID NOT NULL REFERENCES security_engines(id) ON DELETE CASCADE,
    target TEXT NOT NULL,
    target_type TEXT NOT NULL DEFAULT 'host',
    description TEXT,
    authorization_id TEXT,
    authorized_by TEXT NOT NULL DEFAULT 'owner',
    allow_write BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS security_engine_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engine_id UUID NOT NULL REFERENCES security_engines(id) ON DELETE CASCADE,
    scope_id UUID REFERENCES security_engine_scopes(id) ON DELETE SET NULL,
    parent_task_id UUID REFERENCES security_engine_tasks(id) ON DELETE SET NULL,
    target TEXT NOT NULL,
    operation TEXT NOT NULL DEFAULT 'read',
    description TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'sensitive',
    status TEXT NOT NULL DEFAULT 'pending_approval',
    created_by TEXT NOT NULL DEFAULT 'iam',
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    external_task_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    CONSTRAINT ck_security_task_status CHECK (
        status IN ('pending_approval', 'authorized', 'dispatched', 'running',
                   'completed', 'failed', 'cancelled', 'rejected')
    ),
    CONSTRAINT ck_security_task_risk CHECK (
        risk_level IN ('personal', 'operational', 'sensitive', 'protected_core')
    )
);

CREATE TABLE IF NOT EXISTS security_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES security_engine_tasks(id) ON DELETE CASCADE,
    external_id TEXT,
    title TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'informational',
    description TEXT,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    raw JSONB NOT NULL DEFAULT '{}'::jsonb,
    remediation TEXT,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS security_engine_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engine_id UUID REFERENCES security_engines(id) ON DELETE SET NULL,
    task_id UUID REFERENCES security_engine_tasks(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'iam',
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_security_tasks_status
    ON security_engine_tasks (status);
CREATE INDEX IF NOT EXISTS ix_security_findings_task
    ON security_findings (task_id);
