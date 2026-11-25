-- OD-18/OD-19: IAM-initiated non-authority communication with the Creator.

CREATE TABLE IF NOT EXISTS creator_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id TEXT NOT NULL UNIQUE,
    direction TEXT NOT NULL,
    purpose TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    authority_bearing BOOLEAN NOT NULL DEFAULT FALSE,
    request_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_creator_message_direction CHECK (direction IN ('outbound', 'inbound')),
    CONSTRAINT ck_creator_message_purpose CHECK (purpose IN ('question', 'status_update', 'reply')),
    CONSTRAINT ck_creator_message_no_authority CHECK (authority_bearing = false)
);
CREATE INDEX IF NOT EXISTS ix_creator_messages_message_id ON creator_messages (message_id);
CREATE INDEX IF NOT EXISTS ix_creator_messages_created_at ON creator_messages (created_at DESC);
