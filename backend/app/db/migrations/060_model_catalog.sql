-- OD-52 Phase A — live model catalogue fields for IAM's provider registry.
-- A catalogue entry is metadata, never proof of an available free endpoint.

ALTER TABLE discovered_models
    ADD COLUMN IF NOT EXISTS model_type TEXT NOT NULL DEFAULT 'llm',
    ADD COLUMN IF NOT EXISTS access_type TEXT NOT NULL DEFAULT 'free',
    ADD COLUMN IF NOT EXISTS endpoint_status TEXT NOT NULL DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS alias TEXT,
    ADD COLUMN IF NOT EXISTS input_capabilities JSON NOT NULL DEFAULT '[]'::json,
    ADD COLUMN IF NOT EXISTS output_capabilities JSON NOT NULL DEFAULT '[]'::json,
    ADD COLUMN IF NOT EXISTS tool_calling BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS reasoning BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS structured_output BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS api_protocol TEXT NOT NULL DEFAULT 'chat_completions',
    ADD COLUMN IF NOT EXISTS last_tested TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS test_result JSON,
    ADD COLUMN IF NOT EXISTS restrictions JSON NOT NULL DEFAULT '{}'::json,
    ADD COLUMN IF NOT EXISTS metadata_source TEXT,
    ADD COLUMN IF NOT EXISTS last_known_good JSON;

-- Existing rows: derive access from the legacy is_free flag, but never claim
-- an endpoint is available without an actual availability probe.
UPDATE discovered_models
SET access_type = CASE WHEN is_free THEN 'free' ELSE 'paid' END,
    endpoint_status = CASE WHEN is_available THEN 'unknown' ELSE 'unavailable' END,
    metadata_source = COALESCE(metadata_source, 'legacy')
WHERE metadata_source IS NULL OR metadata_source = 'legacy';

ALTER TABLE discovered_models
    DROP CONSTRAINT IF EXISTS ck_discovered_model_type,
    ADD CONSTRAINT ck_discovered_model_type
        CHECK (model_type IN ('llm', 'embedding', 'vision', 'speech', 'image')),
    DROP CONSTRAINT IF EXISTS ck_discovered_model_access,
    ADD CONSTRAINT ck_discovered_model_access
        CHECK (access_type IN ('free', 'paid', 'local')),
    DROP CONSTRAINT IF EXISTS ck_discovered_model_endpoint_status,
    ADD CONSTRAINT ck_discovered_model_endpoint_status
        CHECK (endpoint_status IN ('available', 'unavailable', 'unknown')),
    DROP CONSTRAINT IF EXISTS ck_discovered_model_protocol,
    ADD CONSTRAINT ck_discovered_model_protocol
        CHECK (api_protocol IN ('chat_completions', 'responses', 'embeddings', 'other'));

CREATE INDEX IF NOT EXISTS ix_discovered_models_endpoint_status
    ON discovered_models (endpoint_status);
CREATE INDEX IF NOT EXISTS ix_discovered_models_access_type
    ON discovered_models (access_type);
CREATE UNIQUE INDEX IF NOT EXISTS ux_discovered_models_alias
    ON discovered_models (alias) WHERE alias IS NOT NULL;
