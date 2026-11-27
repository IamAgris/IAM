-- =============================================================================
-- Proposed Doc 35 / OD-55 — Web3 and self-hosted Bitcoin/Lightning foundation
--
-- READ and PREPARE only. This migration creates no execution authority, stores no
-- key material and does not enable any adapter. All feature flags default-off.
-- Every write path (broadcast, pay, swap, channel change) remains blocked until
-- Creator approval integration is implemented under OD-03/OD-04/OD-25.
-- =============================================================================

CREATE TABLE IF NOT EXISTS web3_networks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    native_currency TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'thirdweb',
    rpc_reference TEXT,
    confirmation_blocks INTEGER NOT NULL DEFAULT 12 CHECK (confirmation_blocks >= 0),
    free_tier_verified BOOLEAN NOT NULL DEFAULT false,
    capabilities JSON NOT NULL DEFAULT '{}'::json,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS web3_wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL CHECK (domain IN (
        'operational', 'treasury', 'project', 'development', 'user'
    )),
    provider TEXT NOT NULL,
    network_id UUID REFERENCES web3_networks(id) ON DELETE SET NULL,
    address TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'proposed' CHECK (state IN (
        'proposed', 'verified', 'active', 'suspended', 'retired'
    )),
    verification_method TEXT,
    verification_evidence_ref TEXT,
    policy_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_web3_wallet_address UNIQUE (provider, network_id, address)
);

CREATE INDEX IF NOT EXISTS ix_web3_wallets_domain ON web3_wallets (domain);
CREATE INDEX IF NOT EXISTS ix_web3_wallets_state ON web3_wallets (state);

CREATE TABLE IF NOT EXISTS web3_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    approval_id TEXT,
    wallet_id TEXT,
    chain_id TEXT NOT NULL,
    tx_type TEXT NOT NULL,
    from_address TEXT,
    to_address TEXT NOT NULL,
    token TEXT,
    amount NUMERIC(36, 18),
    gas_estimate NUMERIC(36, 18),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN (
        'draft', 'validated', 'simulated', 'awaiting_approval', 'approved',
        'broadcast', 'confirming', 'confirmed', 'reconciled', 'rejected',
        'expired', 'failed', 'replaced', 'cancelled'
    )),
    idempotency_key TEXT NOT NULL UNIQUE,
    tx_hash TEXT,
    simulation JSON NOT NULL DEFAULT '{}'::json,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_web3_transactions_status ON web3_transactions (status);
CREATE INDEX IF NOT EXISTS ix_web3_transactions_chain ON web3_transactions (chain_id);

CREATE TABLE IF NOT EXISTS web3_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id TEXT NOT NULL,
    contract_address TEXT,
    symbol TEXT NOT NULL,
    name TEXT,
    decimals INTEGER,
    asset_type TEXT NOT NULL DEFAULT 'fungible' CHECK (asset_type IN (
        'native', 'fungible', 'nft', 'multi_token', 'vault_share'
    )),
    source_url TEXT,
    risk_flags JSON NOT NULL DEFAULT '[]'::json,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_web3_asset UNIQUE (chain_id, contract_address, symbol)
);

CREATE TABLE IF NOT EXISTS web3_contracts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_id TEXT NOT NULL,
    address TEXT NOT NULL,
    standard TEXT,
    name TEXT,
    source_verified BOOLEAN NOT NULL DEFAULT false,
    proxy_detected BOOLEAN NOT NULL DEFAULT false,
    owner_analysis JSON NOT NULL DEFAULT '{}'::json,
    risk_flags JSON NOT NULL DEFAULT '[]'::json,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_web3_contract UNIQUE (chain_id, address)
);

CREATE TABLE IF NOT EXISTS node_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL CHECK (provider IN ('bitcoin_core', 'lnd', 'cln')),
    node_id TEXT NOT NULL,
    endpoint_reference TEXT,
    transport TEXT NOT NULL DEFAULT 'tailscale',
    tls_verified BOOLEAN NOT NULL DEFAULT false,
    credential_reference TEXT,
    health_state TEXT NOT NULL DEFAULT 'unknown' CHECK (health_state IN (
        'unknown', 'healthy', 'degraded', 'offline', 'suspended'
    )),
    last_check_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_node_connection UNIQUE (provider, node_id)
);

CREATE TABLE IF NOT EXISTS node_wallet_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES node_connections(id) ON DELETE CASCADE,
    asset TEXT NOT NULL,
    confirmed NUMERIC(36, 8) NOT NULL DEFAULT 0,
    unconfirmed NUMERIC(36, 8) NOT NULL DEFAULT 0,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_node_balances_connection ON node_wallet_balances (connection_id);

CREATE TABLE IF NOT EXISTS bitcoin_utxos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES node_connections(id) ON DELETE CASCADE,
    txid TEXT NOT NULL,
    vout INTEGER NOT NULL,
    address TEXT,
    amount_sats BIGINT NOT NULL CHECK (amount_sats >= 0),
    confirmations INTEGER NOT NULL DEFAULT 0,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_bitcoin_utxo UNIQUE (connection_id, txid, vout)
);

CREATE TABLE IF NOT EXISTS lightning_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES node_connections(id) ON DELETE CASCADE,
    channel_id TEXT NOT NULL,
    peer_id TEXT,
    state TEXT NOT NULL DEFAULT 'unknown',
    capacity_sats BIGINT NOT NULL DEFAULT 0,
    local_balance_sats BIGINT NOT NULL DEFAULT 0,
    remote_balance_sats BIGINT NOT NULL DEFAULT 0,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_lightning_channel UNIQUE (connection_id, channel_id)
);

CREATE TABLE IF NOT EXISTS lightning_peers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES node_connections(id) ON DELETE CASCADE,
    peer_id TEXT NOT NULL,
    alias TEXT,
    connected BOOLEAN NOT NULL DEFAULT false,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_lightning_peer UNIQUE (connection_id, peer_id)
);

CREATE TABLE IF NOT EXISTS lightning_invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES node_connections(id) ON DELETE CASCADE,
    payment_hash TEXT NOT NULL,
    bolt11 TEXT,
    amount_sats BIGINT,
    state TEXT NOT NULL DEFAULT 'unknown',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_lightning_invoice UNIQUE (connection_id, payment_hash)
);

CREATE TABLE IF NOT EXISTS lightning_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES node_connections(id) ON DELETE CASCADE,
    payment_hash TEXT NOT NULL,
    amount_sats BIGINT,
    fee_sats BIGINT,
    state TEXT NOT NULL DEFAULT 'unknown',
    approval_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_lightning_payment UNIQUE (connection_id, payment_hash)
);

CREATE TABLE IF NOT EXISTS lightning_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID NOT NULL REFERENCES node_connections(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    payload JSON NOT NULL DEFAULT '{}'::json,
    reconciled BOOLEAN NOT NULL DEFAULT false,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_lightning_events_connection
    ON lightning_events (connection_id, observed_at);

CREATE TABLE IF NOT EXISTS web3_provider_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    network TEXT,
    available BOOLEAN NOT NULL DEFAULT false,
    latency_ms INTEGER,
    last_check_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_web3_provider_health UNIQUE (provider, network)
);

-- Append-only, hash-chained audit. The trigger prevents UPDATE and DELETE at the
-- database layer; the application verifier recomputes the chain on a schedule.
CREATE TABLE IF NOT EXISTS blockchain_audit_log (
    seq BIGSERIAL PRIMARY KEY,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    target TEXT,
    approval_id TEXT,
    details JSON NOT NULL DEFAULT '{}'::json,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION iam_reject_blockchain_audit_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'blockchain_audit_log is append-only';
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_blockchain_audit_append_only'
    ) THEN
        CREATE TRIGGER trg_blockchain_audit_append_only
        BEFORE UPDATE OR DELETE ON blockchain_audit_log
        FOR EACH ROW EXECUTE FUNCTION iam_reject_blockchain_audit_mutation();
    END IF;
END $$;

-- No wallet, transaction or payment execution authority is created by this migration.
