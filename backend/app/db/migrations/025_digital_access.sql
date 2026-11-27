-- =============================================================================
-- Human assistance queue and encrypted website credential references
-- =============================================================================

CREATE TABLE IF NOT EXISTS assistance_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level TEXT NOT NULL,
    reason TEXT NOT NULL,
    context JSON NOT NULL DEFAULT '{}'::json,
    task_ref TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    resolved_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS website_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site TEXT NOT NULL,
    url TEXT NOT NULL,
    username TEXT NOT NULL,
    secret_ciphertext TEXT NOT NULL,
    secret_env_var TEXT,
    owner_entity TEXT NOT NULL,
    provenance JSON NOT NULL DEFAULT '{}'::json,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    rotated_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
