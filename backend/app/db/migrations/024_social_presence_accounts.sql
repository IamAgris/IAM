-- =============================================================================
-- Verified social presence (OD-30) and online-account lifecycle (Phase 9)
-- =============================================================================

CREATE TABLE IF NOT EXISTS social_presences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    handle TEXT NOT NULL,
    profile_url TEXT NOT NULL,
    owner_entity TEXT NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT false,
    verification_ref TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE online_accounts
    ADD COLUMN IF NOT EXISTS credential_rotated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ;
