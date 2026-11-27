-- IAM memory verification and lifecycle — P0.1 cognitive foundation
-- Adds verification_status to memory_items so verify_memory() persists correctly,
-- plus indexes for expiry sweeps and relationship traversal.

ALTER TABLE memory_items
    ADD COLUMN IF NOT EXISTS verification_status TEXT NOT NULL DEFAULT 'unverified';

ALTER TABLE memory_items
    ADD CONSTRAINT IF NOT EXISTS ck_memory_verification_status
    CHECK (verification_status IN ('unverified', 'verified', 'disputed', 'retracted', 'expired'));

CREATE INDEX IF NOT EXISTS ix_memory_items_verification_status
    ON memory_items (verification_status);

CREATE INDEX IF NOT EXISTS ix_memory_items_expires_at
    ON memory_items (expires_at)
    WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_memory_items_topic_status
    ON memory_items (topic, verification_status);
