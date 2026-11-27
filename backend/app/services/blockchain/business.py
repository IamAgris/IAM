"""Web3 business-opportunity research (proposed Doc 35).

Advisory scoring only. No service is launched, no price is charged and no legal
conclusion is made. Regulatory requirements must be verified separately (OD-31/OD-48).
"""

from typing import Any, Dict, List

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag

CATEGORIES = (
    "web3_saas",
    "blockchain_api",
    "token_gated_membership",
    "nft_digital_product",
    "contract_services",
    "consulting",
    "dapp_development",
    "payments_service",
    "agent_service",
    "infrastructure_service",
)


class Web3BusinessService:
    def policy(self) -> Dict[str, Any]:
        return {"enabled": settings.web3_registry_enabled, "advisory_only": True}

    def evaluate(
        self,
        *,
        category: str,
        estimated_cost_usd: float,
        demand_evidence: List[str],
        competition: List[str],
        legal_review: str = "not_reviewed",
        expected_return_usd: float = 0.0,
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if category not in CATEGORIES:
            raise ProviderDenied(f"unsupported category '{category}'")
        if estimated_cost_usd < 0 or expected_return_usd < 0:
            raise ProviderDenied("costs and returns cannot be negative")
        blockers: List[str] = []
        if legal_review not in ("reviewed", "cleared"):
            blockers.append("legal_review")
        if not demand_evidence:
            blockers.append("demand_evidence")
        margin = expected_return_usd - estimated_cost_usd
        if margin <= 0:
            blockers.append("non_positive_margin")
        return {
            "category": category,
            "estimated_margin_usd": round(margin, 4),
            "competition_count": len(competition),
            "blockers": blockers,
            "recommendation": "do_not_proceed" if blockers else "creator_review",
            "note": "Indicative model only; no revenue or legal clearance is guaranteed.",
        }
