-- IAM Multi-Model Intelligence (OD-51) — encrypted provider connection keys.
-- Secrets are stored encrypted (enc:v1: AES-GCM) by ModelCredentialVault.
-- No plaintext credential is ever written to this table.

CREATE TABLE IF NOT EXISTS model_provider_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    key_alias TEXT NOT NULL,
    key_fingerprint TEXT NOT NULL,
    secret_ciphertext TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'free' CHECK (scope IN ('free', 'paid', 'specialist')),
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    health TEXT NOT NULL DEFAULT 'unknown'
        CHECK (health IN ('unknown', 'healthy', 'unhealthy', 'disabled')),
    failure_count INTEGER NOT NULL DEFAULT 0,
    monthly_limit_usd NUMERIC(12, 6),
    last_checked_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, key_alias)
);

CREATE INDEX IF NOT EXISTS ix_model_provider_keys_provider
    ON model_provider_keys (provider);
