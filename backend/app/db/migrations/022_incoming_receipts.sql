-- =============================================================================
-- Incoming payment receipts (OD-25) — separate authority from spending
-- =============================================================================

CREATE TABLE IF NOT EXISTS incoming_receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID NOT NULL REFERENCES financial_transactions(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    reference TEXT NOT NULL,
    amount NUMERIC(15, 4) NOT NULL,
    authorization_id TEXT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_incoming_receipts_transaction
    ON incoming_receipts (transaction_id);
