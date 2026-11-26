-- =============================================================================
-- Document 26 (OD-45): durable DPIA sign-off record
-- =============================================================================

CREATE TABLE IF NOT EXISTS hbi_dpia_signoffs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reviewer TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approved','rejected')),
    basis TEXT NOT NULL,
    signed_at TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_hbi_dpia_signoffs_decision ON hbi_dpia_signoffs(decision, created_at DESC);
