-- IAM TIPS P6 — Doc 29 (OD-49)
-- Onion service provenance and reputation. Reachability never means trust.

CREATE TABLE IF NOT EXISTS onion_reputation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    address TEXT NOT NULL UNIQUE,
    claimed_operator TEXT,
    status TEXT NOT NULL DEFAULT 'unknown',
    source_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    availability JSONB NOT NULL DEFAULT '{}'::jsonb,
    assessment JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_onion_reputation_status CHECK (
        status IN ('unknown','observed','suspicious','confirmed'))
);
CREATE INDEX IF NOT EXISTS ix_onion_reputation_address ON onion_reputation (address);
