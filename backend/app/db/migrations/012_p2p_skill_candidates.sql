-- =============================================================================
-- P2P skill exchange — untrusted candidates
-- =============================================================================
-- Received skill releases are never active on arrival. They are stored as
-- candidates and must pass local security inspection and creator approval.

CREATE TABLE IF NOT EXISTS p2p_skill_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    envelope_id TEXT NOT NULL UNIQUE,
    publisher TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    version TEXT NOT NULL,
    instructions TEXT NOT NULL,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    checksum TEXT,
    status TEXT NOT NULL DEFAULT 'candidate',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    CONSTRAINT ck_p2p_skill_candidate_status CHECK (
        status IN ('candidate', 'approved', 'rejected')
    )
);

CREATE INDEX IF NOT EXISTS ix_p2p_skill_candidates_status
    ON p2p_skill_candidates (status);
