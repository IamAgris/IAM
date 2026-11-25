-- =============================================================================
-- OEDIE free infrastructure provider adapters (IAM Document 22)
-- =============================================================================
-- External free platforms are candidate infrastructure only. Every provider,
-- quota reading, environment and collected result is recorded. Credential
-- values are NEVER stored here: credential_env holds an environment-variable
-- NAME resolved through the existing secret store / CredentialReference.

CREATE TABLE IF NOT EXISTS free_sandbox_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    provider_type TEXT NOT NULL,
    capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    terms_url TEXT NOT NULL DEFAULT '',
    docs_verified_at TIMESTAMPTZ,
    headless BOOLEAN NOT NULL DEFAULT TRUE,
    registration_status TEXT NOT NULL DEFAULT 'candidate'
        CONSTRAINT ck_free_sandbox_registration_status CHECK (
            registration_status IN (
                'candidate', 'registered', 'pending_creator_approval', 'unavailable'
            )
        ),
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    credential_env TEXT,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS free_sandbox_quota_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES free_sandbox_providers(id) ON DELETE CASCADE,
    used_percent NUMERIC(5,2),
    remaining NUMERIC,
    unit TEXT NOT NULL DEFAULT '',
    resets_at TIMESTAMPTZ,
    source_url TEXT,
    verified_at TIMESTAMPTZ,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_free_sandbox_quota_provider
    ON free_sandbox_quota_snapshots (provider_id);

CREATE TABLE IF NOT EXISTS free_sandbox_environments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES free_sandbox_providers(id) ON DELETE CASCADE,
    external_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    capability TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'provisioning'
        CONSTRAINT ck_free_sandbox_environment_state CHECK (
            state IN (
                'discovered', 'registered', 'provisioning', 'running',
                'stopped', 'completed', 'failed', 'deleted'
            )
        ),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_free_sandbox_environment_task
    ON free_sandbox_environments (task_id);
CREATE INDEX IF NOT EXISTS ix_free_sandbox_environment_provider
    ON free_sandbox_environments (provider_id);

CREATE TABLE IF NOT EXISTS free_sandbox_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment_id UUID NOT NULL REFERENCES free_sandbox_environments(id) ON DELETE CASCADE,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    artifacts JSONB NOT NULL DEFAULT '[]'::jsonb,
    error TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_free_sandbox_result_environment
    ON free_sandbox_results (environment_id);
