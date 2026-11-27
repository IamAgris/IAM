-- =============================================================================
-- Creator approval by email with signed challenges (OD-18 / OD-19)
-- =============================================================================
-- No Creator dashboard. Email carries requests; authority comes only from an
-- ED25519 signature over a one-time challenge verified by CreatorApprovalService.
-- Apply after 003_security_engines.sql.

CREATE TABLE IF NOT EXISTS creator_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id TEXT NOT NULL UNIQUE,
    action_type TEXT NOT NULL,
    target_ref TEXT,
    risk_level TEXT NOT NULL DEFAULT '3',
    summary TEXT NOT NULL,
    reason TEXT,
    consequences JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending',
    requester TEXT NOT NULL DEFAULT 'iam',
    creator_email TEXT,
    channel TEXT NOT NULL DEFAULT 'creator_email',
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT ck_creator_request_risk CHECK (risk_level IN ('1', '2', '3', '4')),
    CONSTRAINT ck_creator_request_status CHECK (
        status IN ('pending', 'approved', 'rejected', 'expired', 'cancelled')
    )
);

CREATE INDEX IF NOT EXISTS ix_creator_requests_status ON creator_requests (status);
CREATE INDEX IF NOT EXISTS ix_creator_requests_action ON creator_requests (action_type);

CREATE TABLE IF NOT EXISTS signed_challenges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES creator_requests(id) ON DELETE CASCADE,
    nonce TEXT NOT NULL UNIQUE,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    payload_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS creator_approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES creator_requests(id) ON DELETE CASCADE,
    decision TEXT NOT NULL,
    signature TEXT NOT NULL,
    signer_id TEXT NOT NULL,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_creator_approval_decision CHECK (
        decision IN ('approved', 'rejected')
    )
);

CREATE TABLE IF NOT EXISTS creator_authorizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type TEXT NOT NULL,
    max_authority_level TEXT NOT NULL DEFAULT '3',
    target_ref TEXT,
    source_request_id UUID REFERENCES creator_requests(id) ON DELETE SET NULL,
    signer_id TEXT NOT NULL,
    scope JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT ck_creator_auth_level CHECK (
        max_authority_level IN ('1', '2', '3', '4')
    )
);

CREATE INDEX IF NOT EXISTS ix_creator_authorizations_action
    ON creator_authorizations (action_type);

CREATE TABLE IF NOT EXISTS communication_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel TEXT NOT NULL,
    direction TEXT NOT NULL,
    actor TEXT NOT NULL DEFAULT 'iam',
    purpose TEXT NOT NULL,
    request_id TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_communication_channel CHECK (
        channel IN ('creator_email', 'operational_email', 'private_user')
    ),
    CONSTRAINT ck_communication_direction CHECK (
        direction IN ('outbound', 'inbound')
    )
);
