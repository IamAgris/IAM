-- IAM Web Knowledge Integration — Doc 29 P4 (OD-49)
-- Browser research enters knowledge only as a governed, verified proposal.

CREATE TABLE IF NOT EXISTS browser_knowledge_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT NOT NULL,
    claim TEXT NOT NULL,
    source_urls JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
    independent_source_count INTEGER NOT NULL DEFAULT 0,
    verification_state TEXT NOT NULL DEFAULT 'unverified',
    legal_decision TEXT NOT NULL DEFAULT 'BLOCKED',
    status TEXT NOT NULL DEFAULT 'pending_review',
    promotion_ref TEXT,
    created_by TEXT NOT NULL,
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT ck_browser_knowledge_proposal_status CHECK (
        status IN ('pending_review','quarantined','approved','rejected')),
    CONSTRAINT ck_browser_knowledge_proposal_verification CHECK (
        verification_state IN ('unverified','single_source','verified'))
);
CREATE INDEX IF NOT EXISTS ix_browser_knowledge_proposals_task_id
    ON browser_knowledge_proposals (task_id);
CREATE INDEX IF NOT EXISTS ix_browser_knowledge_proposals_status
    ON browser_knowledge_proposals (status);
