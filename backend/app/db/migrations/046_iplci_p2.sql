-- IP & Legal Intelligence Phase 2 — proposed OD-48
-- Trademark, patent, design-right and software-IP intelligence records.

CREATE TABLE IF NOT EXISTS ip_legal_trademarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mark_text TEXT NOT NULL,
    owner TEXT NOT NULL,
    jurisdiction TEXT,
    classes JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'registered',
    registration_number TEXT,
    goods_services TEXT,
    logo_hash TEXT,
    territory JSONB,
    filed_at TIMESTAMPTZ,
    registered_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_trademark_status CHECK (
        status IN ('registered','pending','unregistered','withdrawn','expired'))
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_trademarks_status ON ip_legal_trademarks (status);

CREATE TABLE IF NOT EXISTS ip_legal_patents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    publication_number TEXT NOT NULL,
    title TEXT NOT NULL,
    owner TEXT,
    jurisdiction JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending',
    claims JSONB NOT NULL DEFAULT '[]'::jsonb,
    filed_at TIMESTAMPTZ,
    priority_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    family_id TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_patent_status CHECK (
        status IN ('active','granted','pending','expired','lapsed','withdrawn'))
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_patents_status ON ip_legal_patents (status);

CREATE TABLE IF NOT EXISTS ip_legal_design_rights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    right_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    owner TEXT,
    jurisdiction TEXT,
    registration_number TEXT,
    status TEXT NOT NULL DEFAULT 'unregistered',
    expires_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_design_type CHECK (right_type IN (
        'industrial_design','unregistered_design','geographical_indication',
        'plant_variety','semiconductor_layout','domain_name'))
);

CREATE TABLE IF NOT EXISTS ip_legal_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT,
    licence_id TEXT,
    source_url TEXT,
    origin TEXT NOT NULL DEFAULT 'third_party',
    vulnerability_status TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_dependency_origin CHECK (origin IN (
        'original','third_party','ai_generated','copied_public',
        'generated_from_licensed_model','employment_or_contractor','unclear'))
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_dependencies_project ON ip_legal_dependencies (project_id);

CREATE TABLE IF NOT EXISTS ip_legal_sboms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id TEXT NOT NULL,
    components JSONB NOT NULL DEFAULT '[]'::jsonb,
    generated_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_sboms_project ON ip_legal_sboms (project_id);

CREATE TABLE IF NOT EXISTS ip_legal_risk_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,
    subject TEXT NOT NULL,
    jurisdiction TEXT,
    risk TEXT NOT NULL DEFAULT 'UNKNOWN',
    outcome TEXT NOT NULL,
    reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    professional_review_required BOOLEAN NOT NULL DEFAULT FALSE,
    policy_version TEXT NOT NULL DEFAULT '2.0',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_risk_level CHECK (
        risk IN ('LOW','MODERATE','HIGH','CRITICAL','UNKNOWN'))
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_risk_decisions_domain ON ip_legal_risk_decisions (domain);
