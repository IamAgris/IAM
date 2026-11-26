-- =============================================================================
-- Doc 25 Amendment A — research-only financial intelligence
-- Prediction markets, gaming mathematics, investment research, provider gates
-- No table here stores an order, wager, wallet funding or execution authority.
-- =============================================================================

CREATE TABLE IF NOT EXISTS prediction_markets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    market_ref TEXT NOT NULL,
    event_name TEXT NOT NULL,
    outcomes JSON NOT NULL DEFAULT '[]'::json,
    implied_probabilities JSON NOT NULL DEFAULT '{}'::json,
    source_url TEXT,
    legal_status TEXT NOT NULL DEFAULT 'research_only'
        CHECK (legal_status IN ('research_only', 'legal_review_required', 'cleared')),
    real_money_enabled BOOLEAN NOT NULL DEFAULT false,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_prediction_market_ref UNIQUE (platform, market_ref)
);

CREATE TABLE IF NOT EXISTS probability_estimates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id UUID NOT NULL REFERENCES prediction_markets(id) ON DELETE CASCADE,
    outcome TEXT NOT NULL,
    iam_probability NUMERIC(5, 4) NOT NULL CHECK (iam_probability >= 0 AND iam_probability <= 1),
    evidence JSON NOT NULL DEFAULT '[]'::json,
    analyst TEXT NOT NULL DEFAULT 'iam',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_probability_estimates_market_id
    ON probability_estimates (market_id);

CREATE TABLE IF NOT EXISTS forecast_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    market_id UUID NOT NULL REFERENCES prediction_markets(id) ON DELETE CASCADE,
    method TEXT NOT NULL CHECK (method IN ('evidence_weighted', 'base_rate')),
    inputs JSON NOT NULL DEFAULT '{}'::json,
    probabilities JSON NOT NULL DEFAULT '{}'::json,
    evidence JSON NOT NULL DEFAULT '[]'::json,
    rationale TEXT NOT NULL,
    confidence NUMERIC(3, 3) NOT NULL DEFAULT 0,
    market_implied_probabilities_used BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_forecast_runs_market_id ON forecast_runs (market_id);

CREATE TABLE IF NOT EXISTS gaming_research_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game TEXT NOT NULL,
    provider TEXT,
    rtp NUMERIC(5, 4) NOT NULL CHECK (rtp >= 0 AND rtp <= 1),
    house_edge NUMERIC(5, 4) NOT NULL CHECK (house_edge >= 0 AND house_edge <= 1),
    sample_size INTEGER NOT NULL DEFAULT 0 CHECK (sample_size >= 0),
    methodology TEXT NOT NULL,
    findings JSON NOT NULL DEFAULT '{}'::json,
    wagering_enabled BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS investment_research_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_class TEXT NOT NULL CHECK (asset_class IN (
        'stocks', 'etfs', 'commodities', 'futures', 'bonds',
        'precious_metals', 'indices', 'portfolio'
    )),
    symbol TEXT NOT NULL,
    thesis TEXT NOT NULL,
    risk_notes TEXT,
    evidence JSON NOT NULL DEFAULT '{}'::json,
    execution_enabled BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS provider_registry_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    access_model TEXT NOT NULL DEFAULT 'free' CHECK (access_model IN ('free', 'paid', 'mixed')),
    documented_api_and_auth BOOLEAN NOT NULL DEFAULT false,
    commercial_use BOOLEAN NOT NULL DEFAULT false,
    automated_use BOOLEAN NOT NULL DEFAULT false,
    south_africa_supported BOOLEAN NOT NULL DEFAULT false,
    sandbox_available BOOLEAN NOT NULL DEFAULT false,
    licence_required BOOLEAN NOT NULL DEFAULT false,
    licence_requirements_recorded BOOLEAN NOT NULL DEFAULT false,
    gates_reviewed BOOLEAN NOT NULL DEFAULT false,
    notes TEXT,
    adapter_enabled BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_provider_registry_name UNIQUE (name)
);
