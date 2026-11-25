-- Human Public Presence Intelligence / PPIICE (OD-30)

CREATE TABLE IF NOT EXISTS public_people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name TEXT NOT NULL,
    internal_public_id TEXT NOT NULL UNIQUE,
    notes TEXT,
    deanonymized BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_public_person_no_deanonymization CHECK (deanonymized = FALSE)
);
CREATE INDEX IF NOT EXISTS ix_public_people_name ON public_people (canonical_name);

CREATE TABLE IF NOT EXISTS public_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES public_people(id) ON DELETE CASCADE,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_domain TEXT NOT NULL,
    profile_type TEXT NOT NULL DEFAULT 'personal_site',
    stated_name TEXT,
    role TEXT,
    organization TEXT,
    bio TEXT,
    interests JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'self_reported',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    content_hash TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_public_profile_status CHECK (
        status IN ('verified', 'self_reported', 'uncertain', 'corrected')
    )
);
CREATE INDEX IF NOT EXISTS ix_public_profiles_person ON public_profiles (person_id);

CREATE TABLE IF NOT EXISTS presence_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES public_people(id) ON DELETE CASCADE,
    profile_id UUID REFERENCES public_profiles(id) ON DELETE SET NULL,
    claim_type TEXT NOT NULL,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'uncertain',
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    source_url TEXT,
    first_seen_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    supersedes_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_presence_claim_confidence CHECK (confidence BETWEEN 0 AND 1)
);
CREATE INDEX IF NOT EXISTS ix_presence_claims_person ON presence_claims (person_id);

CREATE TABLE IF NOT EXISTS identity_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES public_people(id) ON DELETE CASCADE,
    other_person_id UUID NOT NULL REFERENCES public_people(id) ON DELETE CASCADE,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    result TEXT NOT NULL DEFAULT 'uncertain',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_identity_match_result CHECK (result IN ('same', 'uncertain', 'rejected'))
);

CREATE TABLE IF NOT EXISTS public_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES public_people(id) ON DELETE CASCADE,
    related_person_id UUID,
    organization_name TEXT,
    relationship_type TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_public_relationships_person ON public_relationships (person_id);
