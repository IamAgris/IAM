-- =============================================================================
-- Banking consents (OD-24) and paper trading (Doc 25)
-- =============================================================================

CREATE TABLE IF NOT EXISTS banking_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution TEXT NOT NULL,
    account_ref TEXT NOT NULL,
    capabilities JSON NOT NULL DEFAULT '[]'::json,
    authorization_id TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS paper_portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    cash_balance NUMERIC(15, 4) NOT NULL DEFAULT 0,
    holdings JSON NOT NULL DEFAULT '{}'::json,
    risk_limits JSON NOT NULL DEFAULT '{}'::json,
    emergency_stop BOOLEAN NOT NULL DEFAULT false,
    simulation_only BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS paper_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES paper_portfolios(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,
    price NUMERIC(15, 4) NOT NULL,
    notional NUMERIC(15, 4) NOT NULL,
    fee NUMERIC(15, 4) NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'simulated',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_paper_orders_portfolio ON paper_orders (portfolio_id);
