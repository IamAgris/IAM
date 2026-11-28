-- =============================================================================
-- Core-authorised storage and UWAIE workflow knowledge (OD-27, OD-29)
-- =============================================================================

CREATE TABLE IF NOT EXISTS stored_objects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    s3_key TEXT NOT NULL UNIQUE,
    bucket TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    owner TEXT NOT NULL,
    is_approved_for_sharing BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_stored_object_size CHECK (size_bytes >= 0)
);

CREATE INDEX IF NOT EXISTS ix_stored_objects_owner ON stored_objects (owner);

CREATE TABLE IF NOT EXISTS website_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    url_pattern TEXT NOT NULL,
    steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    verification JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_actor TEXT NOT NULL,
    is_approved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_website_workflows_url_pattern
    ON website_workflows (url_pattern);
