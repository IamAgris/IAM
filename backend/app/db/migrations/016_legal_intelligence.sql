-- Autonomous legal intelligence and government monitoring (OD-31)

CREATE TABLE IF NOT EXISTS legal_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    jurisdiction TEXT NOT NULL,
    authority_type TEXT NOT NULL,
    url TEXT NOT NULL,
    feed_url TEXT,
    reliability TEXT NOT NULL DEFAULT 'official',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_checked_at TIMESTAMPTZ,
    last_content_hash TEXT,
    terms_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_legal_source_authority_type CHECK (
        authority_type IN ('government', 'parliament', 'court', 'regulator',
                           'central_bank', 'tax_authority', 'international', 'security_authority')
    )
);

CREATE TABLE IF NOT EXISTS legal_instruments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES legal_sources(id) ON DELETE RESTRICT,
    jurisdiction TEXT NOT NULL,
    title TEXT NOT NULL,
    authority_name TEXT NOT NULL,
    instrument_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'announcement',
    official_url TEXT NOT NULL,
    document_hash TEXT NOT NULL,
    summary TEXT,
    published_at TIMESTAMPTZ,
    effective_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_legal_instrument_type CHECK (
        instrument_type IN ('constitution', 'legislation', 'regulation', 'court_judgment',
                            'guidance', 'policy', 'bill', 'draft_regulation', 'treaty',
                            'standard', 'announcement')
    ),
    CONSTRAINT ck_legal_instrument_status CHECK (
        status IN ('proposed', 'draft', 'enacted', 'guidance', 'announcement', 'repealed')
    )
);
CREATE INDEX IF NOT EXISTS ix_legal_instruments_source ON legal_instruments (source_id);

CREATE TABLE IF NOT EXISTS legal_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id UUID NOT NULL REFERENCES legal_instruments(id) ON DELETE CASCADE,
    version_label TEXT NOT NULL,
    document_hash TEXT NOT NULL,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    valid_from TIMESTAMPTZ,
    valid_to TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_legal_versions_instrument ON legal_versions (instrument_id);

CREATE TABLE IF NOT EXISTS legal_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id UUID NOT NULL REFERENCES legal_instruments(id) ON DELETE CASCADE,
    change_type TEXT NOT NULL DEFAULT 'new',
    severity TEXT NOT NULL DEFAULT 'informational',
    lifecycle_stage TEXT NOT NULL DEFAULT 'discover',
    authenticated BOOLEAN NOT NULL DEFAULT FALSE,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    creator_approval_reference TEXT,
    professional_review_reference TEXT,
    implemented_at TIMESTAMPTZ,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_legal_change_type CHECK (change_type IN ('new', 'amendment', 'repeal', 'correction')),
    CONSTRAINT ck_legal_change_severity CHECK (severity IN ('critical', 'important', 'informational')),
    CONSTRAINT ck_legal_change_stage CHECK (lifecycle_stage IN (
        'discover', 'authenticate', 'understand', 'assess', 'recommend',
        'authorise', 'implement', 'verify'))
);

CREATE TABLE IF NOT EXISTS legal_impacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    change_id UUID NOT NULL REFERENCES legal_changes(id) ON DELETE CASCADE,
    affected_system TEXT NOT NULL,
    assessment TEXT NOT NULL,
    risk_level TEXT NOT NULL DEFAULT 'low',
    recommendation TEXT NOT NULL,
    obligations JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_legal_impact_risk_level CHECK (risk_level IN ('low', 'medium', 'high', 'critical'))
);
CREATE INDEX IF NOT EXISTS ix_legal_impacts_change ON legal_impacts (change_id);
