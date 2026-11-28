-- IP & Legal Intelligence Phase 6 — confirmed OD-48
-- Signed, versioned compliance policies for the mandatory enforcement gateway.

CREATE TABLE IF NOT EXISTS ip_legal_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version TEXT NOT NULL UNIQUE,
    rules JSONB NOT NULL DEFAULT '{}'::jsonb,
    signed_by TEXT NOT NULL,
    signed_at TIMESTAMPTZ,
    signature TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    change_approval_ref TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_ip_legal_policy_status CHECK (status IN ('draft','active','retired'))
);
CREATE INDEX IF NOT EXISTS ix_ip_legal_policies_status ON ip_legal_policies (status);
