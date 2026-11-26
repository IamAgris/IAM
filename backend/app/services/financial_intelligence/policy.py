"""Cross-cutting policy for prediction, gaming and investment intelligence.

All three departments are research-only in this implementation. Legal eligibility
and provider gates are explicit; nothing here opens an execution, wagering or
payment path.
"""

from typing import Any, Dict

FINANCIAL_INTELLIGENCE_DEPARTMENTS = (
    "income_intelligence",
    "forex_intelligence_and_trading",
    "cryptocurrency_intelligence_and_trading",
    "prediction_market_intelligence",
    "gaming_and_casino_intelligence",
    "investment_and_portfolio_intelligence",
    "payment_and_financial_operations",
    "financial_governance_and_risk",
)

PREDICTION_PLATFORMS = (
    "polymarket",
    "kalshi",
    "predictit",
    "manifold",
    "metaculus",
)

ASSET_CLASSES = (
    "stocks",
    "etfs",
    "commodities",
    "futures",
    "bonds",
    "precious_metals",
    "indices",
    "portfolio",
)

PROVIDER_CATEGORIES = (
    "forex",
    "cryptocurrency",
    "stocks_etfs",
    "commodities_futures_bonds",
    "prediction_markets",
    "gaming_infrastructure",
    "financial_news",
    "economic_data",
    "market_data",
    "crypto_data",
    "blockchain_intelligence",
    "on_chain_analytics",
    "derivatives_intelligence",
    "market_research",
    "technical_analysis",
)

PROVIDER_GATES = (
    "documented_api_and_auth",
    "free_or_paid_access_recorded",
    "commercial_use_permitted",
    "automated_use_permitted",
    "south_africa_supported",
    "demo_or_sandbox_available",
    "licence_or_institutional_requirements_recorded",
    "gates_reviewed",
)

LEGAL_CLEARANCE_ACTION = "prediction_markets.legal_clearance"
LEGAL_CLEARANCE_LEVEL = "4"

SOUTH_AFRICA_NOTICE = (
    "South African legal status must be confirmed separately; a technically "
    "accessible API does not establish lawful participation."
)

RESEARCH_DISCLAIMER = (
    "Market-implied probability is not a forecast. A discrepancy is not "
    "automatically profitable: fees, liquidity, spreads, settlement conditions "
    "and uncertainty in IAM's estimate must be accounted for."
)


class IntelligenceDenied(PermissionError):
    """Raised when a research action breaks a research-only boundary."""


def provider_eligibility(entry: Any) -> Dict[str, Any]:
    """Return §18 gate results for a provider registry entry."""
    gates = {
        "documented_api_and_auth": bool(getattr(entry, "documented_api_and_auth", False)),
        "free_or_paid_access_recorded": bool(getattr(entry, "access_model", None) in ("free", "paid", "mixed")),
        "commercial_use_permitted": bool(getattr(entry, "commercial_use", False)),
        "automated_use_permitted": bool(getattr(entry, "automated_use", False)),
        "south_africa_supported": bool(getattr(entry, "south_africa_supported", False)),
        "demo_or_sandbox_available": bool(getattr(entry, "sandbox_available", False)),
        "licence_or_institutional_requirements_recorded": bool(
            getattr(entry, "licence_requirements_recorded", False)
        ),
        "gates_reviewed": bool(getattr(entry, "gates_reviewed", False)),
    }
    missing = [name for name, passed in gates.items() if not passed]
    return {"gates": gates, "missing": missing, "adapter_eligible": not missing}


def require_eligible_provider(entry: Any) -> None:
    """Refuse to enable an adapter whose §18 gates are not all satisfied."""
    result = provider_eligibility(entry)
    if not result["adapter_eligible"]:
        raise IntelligenceDenied(
            "provider adapter cannot be enabled; missing gates: "
            + ", ".join(result["missing"])
        )
