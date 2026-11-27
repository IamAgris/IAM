-- IPLCI legal validation workflow — qualified-counsel completion track.

CREATE TABLE IF NOT EXISTS ip_legal_validation_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    subject TEXT NOT NULL,
    jurisdiction TEXT,
    question TEXT NOT NULL,
    official_source_url TEXT,
    provision_ref TEXT,
    assigned_counsel TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    evidence_ref TEXT,
    reviewer_reference TEXT,
    reviewed_at TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    notes TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_validation_status CHECK (
        status IN ('pending','in_review','verified','rejected','superseded'))
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_validation_status ON ip_legal_validation_tasks (status);
