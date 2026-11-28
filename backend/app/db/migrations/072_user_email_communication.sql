-- Opt-in email carrier for private user communication (OD-59 / Doc 39).
-- Extends the existing per-visitor conversation store; no new message system.
-- Addresses and bodies are field-encrypted by the service; email_hash is a
-- one-way lookup key. An email address is not identity proof until verified.

CREATE TABLE IF NOT EXISTS user_email_opt_ins (
    id UUID PRIMARY KEY,
    visitor_id UUID NOT NULL UNIQUE REFERENCES anonymous_visitors(id) ON DELETE CASCADE,
    email_ciphertext TEXT NOT NULL,
    email_hash TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'pending',
    verification_token_hash TEXT,
    verification_expires_at TIMESTAMPTZ,
    email_session_token TEXT,
    email_thread_id UUID,
    opted_in_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_at TIMESTAMPTZ,
    opted_out_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_user_email_opt_in_status CHECK (status IN ('pending', 'verified', 'revoked'))
);

CREATE INDEX IF NOT EXISTS ix_user_email_opt_ins_visitor_id ON user_email_opt_ins (visitor_id);
CREATE INDEX IF NOT EXISTS ix_user_email_opt_ins_email_hash ON user_email_opt_ins (email_hash);

CREATE TABLE IF NOT EXISTS user_email_outbox (
    id UUID PRIMARY KEY,
    visitor_id UUID NOT NULL REFERENCES anonymous_visitors(id) ON DELETE CASCADE,
    recipient_ciphertext TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_ciphertext TEXT NOT NULL,
    transport TEXT NOT NULL DEFAULT 'smtp',
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ,
    CONSTRAINT ck_user_email_outbox_status CHECK (status IN ('pending', 'sent', 'failed', 'dead_letter'))
);

CREATE INDEX IF NOT EXISTS ix_user_email_outbox_visitor_id ON user_email_outbox (visitor_id);
CREATE INDEX IF NOT EXISTS ix_user_email_outbox_status ON user_email_outbox (status);

CREATE TABLE IF NOT EXISTS user_email_inbound (
    id UUID PRIMARY KEY,
    provider_message_id TEXT NOT NULL UNIQUE,
    visitor_id UUID NOT NULL REFERENCES anonymous_visitors(id) ON DELETE CASCADE,
    thread_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_user_email_inbound_visitor_id ON user_email_inbound (visitor_id);
