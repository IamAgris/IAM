-- IP & Legal Intelligence Phase 4 — proposed OD-48
-- Jurisdiction rules, official sources, verification, obligations,
-- business reviews and research-ethics reviews.

CREATE TABLE IF NOT EXISTS ip_legal_jurisdiction_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jurisdiction TEXT NOT NULL,
    domain TEXT NOT NULL,
    provision TEXT NOT NULL,
    source_ref TEXT,
    verification_status TEXT NOT NULL DEFAULT 'requires_verification',
    effective_from TIMESTAMPTZ,
    verified_by TEXT,
    verified_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_jurisdiction_rules_jurisdiction
    ON ip_legal_jurisdiction_rules (jurisdiction);

CREATE TABLE IF NOT EXISTS ip_legal_official_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    authority TEXT NOT NULL,
    authority_type TEXT NOT NULL DEFAULT 'regulator',
    jurisdiction TEXT NOT NULL,
    url TEXT NOT NULL,
    verified_by TEXT,
    verified_at TIMESTAMPTZ,
    last_checked_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ip_legal_knowledge_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim TEXT NOT NULL,
    jurisdiction TEXT,
    source_url TEXT,
    provision_ref TEXT,
    document_type TEXT NOT NULL DEFAULT 'guidance',
    status TEXT NOT NULL DEFAULT 'unverified',
    reviewer TEXT,
    reviewed_at TIMESTAMPTZ,
    checked_at TIMESTAMPTZ,
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_knowledge_status CHECK (
        status IN ('unverified','requires_verification','verified','superseded'))
);

CREATE TABLE IF NOT EXISTS ip_legal_obligations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    jurisdiction TEXT,
    obligation TEXT NOT NULL,
    source_ref TEXT,
    responsible_party TEXT,
    due_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'open',
    evidence_ref TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_obligation_status CHECK (
        status IN ('open','in_progress','completed','overdue'))
);

CREATE TABLE IF NOT EXISTS ip_legal_business_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    activity TEXT NOT NULL,
    business_domain TEXT NOT NULL,
    jurisdiction TEXT,
    risk TEXT NOT NULL DEFAULT 'UNKNOWN',
    outcome TEXT NOT NULL,
    obligations JSONB NOT NULL DEFAULT '[]'::jsonb,
    blockers JSONB NOT NULL DEFAULT '[]'::jsonb,
    human_approval_required BOOLEAN NOT NULL DEFAULT FALSE,
    approval_reference TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ip_legal_ethics_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    jurisdiction TEXT,
    risk TEXT NOT NULL DEFAULT 'UNKNOWN',
    outcome TEXT NOT NULL,
    requirements JSONB NOT NULL DEFAULT '[]'::jsonb,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_ethics_type CHECK (
        review_type IN ('research_ethics','identity','cross_border'))
);
