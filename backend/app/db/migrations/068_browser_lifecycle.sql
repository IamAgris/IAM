-- IAM browser lifecycle evidence — Doc 29 P8 (OD-49)
-- Version snapshots, backups, updates, recovery and retirement records.

CREATE TABLE IF NOT EXISTS browser_lifecycle_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component TEXT NOT NULL,
    event_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'applied',
    version TEXT,
    checksum TEXT,
    backup_ref TEXT,
    actor TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_browser_lifecycle_event CHECK (
        event_type IN ('snapshot','update','backup','recovery','retire','rollback')),
    CONSTRAINT ck_browser_lifecycle_status CHECK (
        status IN ('applied','verified','failed','retired'))
);
CREATE INDEX IF NOT EXISTS ix_browser_lifecycle_records_component
    ON browser_lifecycle_records (component);
CREATE INDEX IF NOT EXISTS ix_browser_lifecycle_records_event_type
    ON browser_lifecycle_records (event_type);
