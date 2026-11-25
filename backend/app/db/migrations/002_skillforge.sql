-- =============================================================================
-- IAM Skill Forge — native skill creation and lifecycle management
-- =============================================================================
-- Adds a versioned, permission-scoped skill registry separate from the legacy
-- `skills` proficiency table. Apply after 001_initial_schema.sql.

CREATE TABLE IF NOT EXISTS skillforge_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    origin TEXT NOT NULL DEFAULT 'native',
    provider TEXT,
    category TEXT,
    classification TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    version TEXT NOT NULL DEFAULT '1.0.0',
    manifest JSONB NOT NULL DEFAULT '{}',
    permissions JSONB NOT NULL DEFAULT '[]',
    network_access BOOLEAN NOT NULL DEFAULT FALSE,
    filesystem_access TEXT NOT NULL DEFAULT 'none',
    requires_creator_approval BOOLEAN NOT NULL DEFAULT FALSE,
    path TEXT,
    checksum TEXT,
    created_by TEXT NOT NULL DEFAULT 'iam',
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    activated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_skillforge_origin CHECK (origin IN ('native', 'imported')),
    CONSTRAINT ck_skillforge_classification CHECK (
        classification IN ('personal', 'operational', 'sensitive', 'protected_core')
    ),
    CONSTRAINT ck_skillforge_status CHECK (
        status IN ('draft', 'testing', 'pending_approval', 'published',
                   'active', 'quarantined', 'archived')
    ),
    CONSTRAINT ck_skillforge_filesystem_access CHECK (
        filesystem_access IN ('none', 'scoped', 'full')
    ),
    CONSTRAINT ck_skillforge_provider CHECK (
        provider IS NULL OR provider IN
        ('openai', 'nvidia', 'google', 'anthropic', 'microsoft', 'community')
    )
);

CREATE INDEX IF NOT EXISTS ix_skillforge_packages_skill_id
    ON skillforge_packages (skill_id);
CREATE INDEX IF NOT EXISTS ix_skillforge_packages_status
    ON skillforge_packages (status);

CREATE TABLE IF NOT EXISTS skillforge_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES skillforge_packages(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    manifest JSONB NOT NULL DEFAULT '{}',
    permissions JSONB NOT NULL DEFAULT '[]',
    checksum TEXT,
    change_note TEXT,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_skillforge_version_semver CHECK (version ~ '^\d+\.\d+\.\d+$')
);

CREATE TABLE IF NOT EXISTS skillforge_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES skillforge_packages(id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    test_type TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    details JSONB NOT NULL DEFAULT '[]',
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skillforge_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID REFERENCES skillforge_packages(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'iam',
    details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS skillforge_permission_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    package_id UUID NOT NULL REFERENCES skillforge_packages(id) ON DELETE CASCADE,
    permission TEXT NOT NULL,
    granted_by TEXT NOT NULL DEFAULT 'owner',
    reason TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
