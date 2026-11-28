-- AI Assistant Interoperability and Technology Learning Lab (OD-28)

CREATE TABLE IF NOT EXISTS assistant_systems (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    vendor TEXT NOT NULL,
    official_docs_url TEXT NOT NULL,
    integration_method TEXT NOT NULL DEFAULT 'official_interface_only',
    public_capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
    terms_url TEXT,
    status TEXT NOT NULL DEFAULT 'studied',
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_assistant_system_status CHECK (status IN ('studied', 'integration_available', 'replicated'))
);

CREATE TABLE IF NOT EXISTS assistant_research_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assistant_id UUID NOT NULL REFERENCES assistant_systems(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    observation TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_date TIMESTAMPTZ,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    status TEXT NOT NULL DEFAULT 'observation',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_assistant_note_status CHECK (status IN ('observation', 'verified', 'uncertain'))
);
CREATE INDEX IF NOT EXISTS ix_assistant_notes_assistant ON assistant_research_notes (assistant_id);

CREATE TABLE IF NOT EXISTS assistant_adapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assistant_id UUID NOT NULL REFERENCES assistant_systems.id ON DELETE CASCADE,
    name TEXT NOT NULL,
    interface_type TEXT NOT NULL,
    endpoint_template TEXT,
    auth_method TEXT NOT NULL DEFAULT 'operator_provided_credential',
    requires_credential BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_assistant_adapter_interface CHECK (
        interface_type IN ('official_skill', 'app_intents', 'shortcuts',
                           'automation_studio', 'official_api', 'documentation_only')
    )
);

CREATE TABLE IF NOT EXISTS replication_experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capability TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    method TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    result TEXT NOT NULL DEFAULT 'planned',
    isolated BOOLEAN NOT NULL DEFAULT TRUE,
    production_adopted BOOLEAN NOT NULL DEFAULT FALSE,
    creator_approval_reference TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_replication_experiment_result CHECK (
        result IN ('planned', 'running', 'succeeded', 'failed')
    )
);

CREATE TABLE IF NOT EXISTS capability_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assistant_id UUID NOT NULL REFERENCES assistant_systems.id ON DELETE CASCADE,
    capability TEXT NOT NULL,
    rating INTEGER NOT NULL,
    evidence_note TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_capability_comparison_rating CHECK (rating BETWEEN 0 AND 5)
);
