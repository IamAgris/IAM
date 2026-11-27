-- =============================================================================
-- Scoped API credentials for backend authentication
-- =============================================================================
-- Only key hashes are stored. Creator authority is independent (OD-19).

CREATE TABLE IF NOT EXISTS api_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    key_hash TEXT NOT NULL UNIQUE,
    scope TEXT NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by TEXT NOT NULL DEFAULT 'bootstrap',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT ck_api_credential_scope CHECK (
        scope IN ('user', 'service', 'operator', 'admin')
    )
);

CREATE INDEX IF NOT EXISTS ix_api_credentials_key_hash
    ON api_credentials (key_hash);
