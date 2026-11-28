"""Doc 25 §18 candidate provider catalogue — names and categories only.

Nothing here asserts that a provider is available, lawful, free, or safe to use.
All gates are recorded as unreviewed; an operator must verify them before an
adapter can be enabled. No credentials, URLs or executable endpoints are stored.
"""

from dataclasses import dataclass

from app.services.financial_intelligence.policy import SOUTH_AFRICA_NOTICE

RESEARCH_NOTE = "Candidate from Doc 25 §18; gates unverified, no adapter enabled."


@dataclass(frozen=True)
class ProviderCandidate:
    name: str
    category: str
    note: str = RESEARCH_NOTE


_PREDICTION_NOTE = (
    RESEARCH_NOTE + " Prediction markets require separate legal assessment; public research only. "
    + SOUTH_AFRICA_NOTICE
)
_GAMING_NOTE = (
    RESEARCH_NOTE + " Industry and technology research only; no wagering or account funding."
)

PROVIDER_CANDIDATES = (
    # Trading venues
    ProviderCandidate("OANDA", "forex"),
    ProviderCandidate("MetaTrader brokers", "forex"),
    ProviderCandidate("Kraken", "cryptocurrency"),
    ProviderCandidate("Coinbase", "cryptocurrency"),
    ProviderCandidate("Binance", "cryptocurrency"),
    ProviderCandidate("Interactive Brokers", "stocks_etfs"),
    ProviderCandidate("Alpaca", "stocks_etfs"),
    ProviderCandidate("CME-connected brokers", "commodities_futures_bonds"),
    ProviderCandidate("Authorised commodity brokers", "commodities_futures_bonds"),
    ProviderCandidate("Institutional data providers", "commodities_futures_bonds"),
    # Prediction markets
    ProviderCandidate("Polymarket", "prediction_markets", _PREDICTION_NOTE),
    ProviderCandidate("Kalshi", "prediction_markets", _PREDICTION_NOTE),
    ProviderCandidate("PredictIt", "prediction_markets", _PREDICTION_NOTE),
    ProviderCandidate("Manifold Markets", "prediction_markets", _PREDICTION_NOTE),
    ProviderCandidate("Metaculus", "prediction_markets", _PREDICTION_NOTE),
    # Gaming / iGaming infrastructure
    ProviderCandidate("Evolution", "gaming_infrastructure", _GAMING_NOTE),
    ProviderCandidate("Pragmatic Play", "gaming_infrastructure", _GAMING_NOTE),
    ProviderCandidate("Play'n GO", "gaming_infrastructure", _GAMING_NOTE),
    ProviderCandidate("Light & Wonder", "gaming_infrastructure", _GAMING_NOTE),
    ProviderCandidate("EveryMatrix", "gaming_infrastructure", _GAMING_NOTE),
    ProviderCandidate("SOFTSWISS", "gaming_infrastructure", _GAMING_NOTE),
    ProviderCandidate("Gaming Innovation Group", "gaming_infrastructure", _GAMING_NOTE),
    # Financial news and economic data
    ProviderCandidate("Bloomberg", "financial_news"),
    ProviderCandidate("Reuters", "financial_news"),
    ProviderCandidate("FRED", "economic_data"),
    ProviderCandidate("Trading Economics", "economic_data"),
    # Market data
    ProviderCandidate("LSEG", "market_data"),
    ProviderCandidate("Polygon.io", "market_data"),
    # Crypto data and analytics
    ProviderCandidate("CoinGecko", "crypto_data"),
    ProviderCandidate("CoinMarketCap", "crypto_data"),
    ProviderCandidate("Glassnode", "blockchain_intelligence"),
    ProviderCandidate("CryptoQuant", "blockchain_intelligence"),
    ProviderCandidate("Dune", "on_chain_analytics"),
    ProviderCandidate("DefiLlama", "on_chain_analytics"),
    ProviderCandidate("Coinglass", "derivatives_intelligence"),
    # Research and analysis
    ProviderCandidate("Financial Modeling Prep", "market_research"),
    ProviderCandidate("TradingView", "technical_analysis"),
    # Proposed Doc 35 — all gates unverified until the operator reviews them.
    # thirdweb remains OD-23 free-only; the node entries are self-hosted, not providers
    # that hold IAM funds. No adapter is enabled by adding a catalogue entry.
    ProviderCandidate(
        "thirdweb", "blockchain_intelligence",
        "OD-23 free tier only; self-hosted open-source Engine permitted; paid tiers forbidden.",
    ),
    ProviderCandidate(
        "Umbrel Bitcoin Core", "blockchain_intelligence",
        "Self-hosted node; read-only RPC via an in-Umbrel connector; separate identity.",
    ),
    ProviderCandidate(
        "Umbrel LND", "blockchain_intelligence",
        "Self-hosted Lightning node 1; restricted macaroon; separate identity from CLN.",
    ),
    ProviderCandidate(
        "Umbrel Core Lightning", "blockchain_intelligence",
        "Self-hosted Lightning node 2; restricted rune; separate identity from LND.",
    ),
)
