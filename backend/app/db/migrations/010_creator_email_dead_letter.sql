-- =============================================================================
-- Creator email dead-letter queue
-- =============================================================================
-- Delivery failures beyond CREATOR_EMAIL_MAX_ATTEMPTS stop being retried and
-- are surfaced for operator attention. Approval authority is unaffected.

CREATE TABLE IF NOT EXISTS creator_email_dead_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL UNIQUE,
    recipient TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_creator_dead_letter_request
    ON creator_email_dead_letters (request_id);
