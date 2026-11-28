-- =============================================================================
-- WebAuthn passkeys and TOTP enrollment (Phase 9)
-- =============================================================================

CREATE TABLE IF NOT EXISTS webauthn_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_credential_id UUID NOT NULL REFERENCES website_credentials(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL,
    challenge TEXT NOT NULL,
    rp_id TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS passkey_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_credential_id UUID NOT NULL REFERENCES website_credentials(id) ON DELETE CASCADE,
    credential_id TEXT NOT NULL UNIQUE,
    public_key_pem TEXT NOT NULL,
    rp_id TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS totp_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    website_credential_id UUID NOT NULL REFERENCES website_credentials(id) ON DELETE CASCADE,
    secret_ciphertext TEXT NOT NULL,
    issuer TEXT,
    account TEXT,
    recovery_hashes JSON NOT NULL DEFAULT '[]'::json,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
