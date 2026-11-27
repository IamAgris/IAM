-- Doc 18 / OD-34: external AI identity verification, structured interviews
-- and richer relationship registry fields on existing deployments.

ALTER TABLE external_agents
    ADD COLUMN IF NOT EXISTS claimed_identity TEXT,
    ADD COLUMN IF NOT EXISTS creator TEXT,
    ADD COLUMN IF NOT EXISTS operator TEXT,
    ADD COLUMN IF NOT EXISTS stated_purpose TEXT,
    ADD COLUMN IF NOT EXISTS identity_verification TEXT NOT NULL DEFAULT 'self-reported',
    ADD COLUMN IF NOT EXISTS verification_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS expertise JSONB NOT NULL DEFAULT '[]'::jsonb;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_agent_identity_verification'
    ) THEN
        ALTER TABLE external_agents
            ADD CONSTRAINT ck_agent_identity_verification
            CHECK (identity_verification IN ('self-reported', 'verified'));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS agent_interviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES external_agents(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT,
    provenance TEXT,
    risk_level TEXT NOT NULL DEFAULT 'low',
    validated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_interview_risk CHECK (risk_level IN ('low', 'medium', 'high'))
);
CREATE INDEX IF NOT EXISTS ix_agent_interviews_agent_id ON agent_interviews (agent_id);
CREATE INDEX IF NOT EXISTS ix_agent_interviews_created_at ON agent_interviews (created_at DESC);
