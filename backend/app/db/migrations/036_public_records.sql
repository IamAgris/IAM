-- Public records, vital events and estate intelligence (OD-30)

CREATE TABLE IF NOT EXISTS public_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    jurisdiction TEXT NOT NULL,
    category TEXT NOT NULL,
    url TEXT NOT NULL,
    access_condition TEXT NOT NULL DEFAULT 'public',
    reliability TEXT NOT NULL DEFAULT 'unverified',
    terms_url TEXT,
    last_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_public_source_access_condition
        CHECK (access_condition IN ('public', 'requires_authority', 'restricted', 'paid', 'unknown')),
    CONSTRAINT ck_public_source_reliability
        CHECK (reliability IN ('official', 'independent', 'self_reported', 'unverified'))
);

CREATE TABLE IF NOT EXISTS public_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID NOT NULL REFERENCES public_sources(id) ON DELETE RESTRICT,
    category TEXT NOT NULL,
    jurisdiction TEXT NOT NULL,
    subject_name TEXT,
    title TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ,
    source_url TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    facts JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'uncertain',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    legal_authority_reference TEXT,
    is_statistical BOOLEAN NOT NULL DEFAULT FALSE,
    is_correction BOOLEAN NOT NULL DEFAULT FALSE,
    supersedes_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_public_record_status
        CHECK (status IN ('verified', 'self_reported', 'uncertain', 'allegation', 'restricted')),
    CONSTRAINT ck_public_record_confidence CHECK (confidence >= 0 AND confidence <= 1)
);
CREATE INDEX IF NOT EXISTS ix_public_records_subject ON public_records (subject_name);
CREATE INDEX IF NOT EXISTS ix_public_records_category_jurisdiction
    ON public_records (category, jurisdiction);

CREATE TABLE IF NOT EXISTS record_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_record_id UUID NOT NULL REFERENCES public_records(id) ON DELETE CASCADE,
    to_record_id UUID NOT NULL REFERENCES public_records(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_record_relationship_type
        CHECK (relation_type IN ('same_entity', 'related_entity', 'conflict', 'correction')),
    CONSTRAINT ck_record_relationship_confidence CHECK (confidence >= 0 AND confidence <= 1)
);
CREATE INDEX IF NOT EXISTS ix_record_relationships_from ON record_relationships (from_record_id);
