-- =============================================================================
# AI Communication & Collaboration tables (Module C / Phase 10)
# =============================================================================

CREATE TABLE IF NOT EXISTS ai_identity_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    model_id TEXT,
    communication_channel TEXT NOT NULL,
    is_local BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    communication_permitted BOOLEAN NOT NULL DEFAULT false,
    trust_level TEXT NOT NULL DEFAULT 'untrusted',
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_capability_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_identity_id UUID NOT NULL REFERENCES ai_identity_registry(id) ON DELETE CASCADE,
    capability TEXT NOT NULL,
    confidence_score INTEGER NOT NULL DEFAULT 50,
    last_verified_at TIMESTAMPTZ,
    evidence JSON NOT NULL DEFAULT '[]'::json
);

CREATE TABLE IF NOT EXISTS ai_conversation_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_identity_id UUID NOT NULL REFERENCES ai_identity_registry(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    topic TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_human_mediated BOOLEAN NOT NULL DEFAULT false,
    message_count INTEGER NOT NULL DEFAULT 0,
    last_message_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES ai_conversation_threads(id) ON DELETE CASCADE,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text',
    confidence_score INTEGER,
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    token_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_context_exchange (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_identity_id UUID NOT NULL REFERENCES ai_identity_registry(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES ai_conversation_threads(id) ON DELETE SET NULL,
    context_type TEXT NOT NULL,
    content JSON NOT NULL DEFAULT '{}'::json,
    is_shared BOOLEAN NOT NULL DEFAULT false,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_response_verification (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID NOT NULL REFERENCES ai_conversation_messages(id) ON DELETE CASCADE,
    original_claim TEXT NOT NULL,
    verified_claim TEXT,
    verification_method TEXT NOT NULL,
    confidence INTEGER NOT NULL DEFAULT 50,
    evidence_references JSON NOT NULL DEFAULT '[]'::json,
    verified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_by TEXT NOT NULL DEFAULT 'iam'
);

CREATE TABLE IF NOT EXISTS ai_reputation_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_identity_id UUID NOT NULL REFERENCES ai_identity_registry(id) ON DELETE CASCADE,
    accuracy_score INTEGER NOT NULL DEFAULT 50,
    honesty_score INTEGER NOT NULL DEFAULT 50,
    helpfulness_score INTEGER NOT NULL DEFAULT 50,
    total_interactions INTEGER NOT NULL DEFAULT 0,
    correct_predictions INTEGER NOT NULL DEFAULT 0,
    incorrect_predictions INTEGER NOT NULL DEFAULT 0,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_communication_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_identity_id UUID NOT NULL REFERENCES ai_identity_registry(id) ON DELETE CASCADE,
    can_share_project_context BOOLEAN NOT NULL DEFAULT false,
    can_share_research_findings BOOLEAN NOT NULL DEFAULT false,
    can_share_code BOOLEAN NOT NULL DEFAULT false,
    can_receive_private_data BOOLEAN NOT NULL DEFAULT false,
    can_initiate_contact BOOLEAN NOT NULL DEFAULT false,
    can_receive_responses BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS human_communication_bridge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_identity_id UUID NOT NULL REFERENCES ai_identity_registry(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES ai_conversation_threads(id) ON DELETE SET NULL,
    iam_message TEXT NOT NULL,
    human_response TEXT,
    ai_response TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_communication_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ai_identity_id UUID REFERENCES ai_identity_registry(id) ON DELETE SET NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    event_type TEXT NOT NULL,
    target TEXT,
    details JSON NOT NULL DEFAULT '{}'::json,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Check constraints
ALTER TABLE ai_identity_registry
    ADD CONSTRAINT ck_ai_identity_trust_level
        CHECK (trust_level IN ('untrusted', 'trusted', 'restricted'));

ALTER TABLE ai_capability_registry
    ADD CONSTRAINT ck_ai_capability_confidence_score
        CHECK (confidence_score BETWEEN 0 AND 100);

ALTER TABLE ai_conversation_threads
    ADD CONSTRAINT ck_ai_conversation_status
        CHECK (status IN ('active', 'paused', 'completed', 'archived'));

ALTER TABLE ai_conversation_messages
    ADD CONSTRAINT ck_ai_message_sender
        CHECK (sender IN ('iam', 'ai', 'human'));

ALTER TABLE ai_conversation_messages
    ADD CONSTRAINT ck_ai_message_confidence
        CHECK (confidence_score IS NULL OR confidence_score BETWEEN 0 AND 100);

ALTER TABLE ai_conversation_messages
    ADD CONSTRAINT ck_ai_message_verification
        CHECK (verification_status IN ('unverified', 'verified', 'disputed', 'false'));

ALTER TABLE ai_response_verification
    ADD CONSTRAINT ck_ai_response_verification_confidence
        CHECK (confidence BETWEEN 0 AND 100);

ALTER TABLE ai_response_verification
    ADD CONSTRAINT ck_ai_response_verification_method
        CHECK (verification_method IN ('independent_reasoning', 'external_source', 'code_execution', 'human_review'));

ALTER TABLE ai_reputation_records
    ADD CONSTRAINT ck_ai_reputation_accuracy_score
        CHECK (accuracy_score BETWEEN 0 AND 100);

ALTER TABLE ai_reputation_records
    ADD CONSTRAINT ck_ai_reputation_honesty_score
        CHECK (honesty_score BETWEEN 0 AND 100);

ALTER TABLE ai_reputation_records
    ADD CONSTRAINT ck_ai_reputation_helpfulness_score
        CHECK (helpfulness_score BETWEEN 0 AND 100);

ALTER TABLE human_communication_bridge
    ADD CONSTRAINT ck_human_communication_status
        CHECK (status IN ('pending', 'awaiting_human', 'completed', 'cancelled'));
