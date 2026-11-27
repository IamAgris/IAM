-- =============================================================================
-- Creator email outbox (OD-18 delivery + CM-10 retry)
-- =============================================================================
-- Approval authority is unchanged: only signed challenges decide. This table
-- only tracks delivery of the explanatory email to the Creator address.

CREATE TABLE IF NOT EXISTS creator_email_outbox (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL UNIQUE,
    recipient TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    transport TEXT NOT NULL DEFAULT 'log',
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sent_at TIMESTAMPTZ,
    CONSTRAINT ck_creator_outbox_status CHECK (
        status IN ('pending', 'sent', 'failed', 'skipped')
    )
);

CREATE INDEX IF NOT EXISTS ix_creator_outbox_status
    ON creator_email_outbox (status);
