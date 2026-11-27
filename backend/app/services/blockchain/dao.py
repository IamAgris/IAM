"""DAO and governance research with advisory recommendations (proposed Doc 33).

Voting is never automatic. Recommendations are deterministic and evidence-based;
final authority stays with the Creator through the signed approval flow.
"""

from typing import Any, Dict, List

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag


class DaoGovernanceService:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_dao_enabled,
            "autonomous_voting": False,
            "recommendations_advisory_only": True,
            "vote_requires_signed_approval": "web3.dao.vote",
        }

    def analyze_proposal(
        self,
        *,
        dao: str,
        proposal_id: str,
        summary: str,
        requested_amount_usd: float = 0.0,
        source_url: str = "",
        indicators: List[str] | None = None,
    ) -> Dict[str, Any]:
        require_flag(settings.web3_dao_enabled, "DAO intelligence is disabled")
        if not dao or not proposal_id or not summary:
            raise ProviderDenied("dao, proposal_id and summary are required")
        signals = list(indicators or [])
        concerns = [
            signal
            for signal in signals
            if signal in (
                "anonymous_proposer",
                "unverified_multisig",
                "unlimited_token_mint",
                "emergency_powers",
                "no_timelock",
            )
        ]
        risk = "high" if concerns else ("medium" if requested_amount_usd > 0 else "low")
        return {
            "dao": dao,
            "proposal_id": proposal_id,
            "summary": summary,
            "requested_amount_usd": requested_amount_usd,
            "source_url": source_url,
            "risk": risk,
            "concerns": concerns,
            "note": "Community signals are not evidence of legitimacy.",
        }

    def recommendation(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        require_flag(settings.web3_dao_enabled, "DAO intelligence is disabled")
        risk = analysis.get("risk")
        if risk not in ("low", "medium", "high"):
            raise ProviderDenied("a completed proposal analysis is required")
        decision = "abstain" if risk == "high" else "review"
        return {
            "recommendation": decision,
            "rationale": (
                "high risk indicators present; abstain pending independent review"
                if decision == "abstain"
                else "no blocking indicators; Creator review required before voting"
            ),
            "advisory_only": True,
            "execution_enabled": False,
        }

    def prepare_vote(
        self, *, dao: str, proposal_id: str, choice: str
    ) -> Dict[str, Any]:
        require_flag(settings.web3_dao_enabled, "DAO intelligence is disabled")
        if choice not in ("for", "against", "abstain"):
            raise ProviderDenied("choice must be for, against or abstain")
        return {
            "status": "prepared",
            "dao": dao,
            "proposal_id": proposal_id,
            "choice": choice,
            "approval_action": "web3.dao.vote",
            "approval_required": True,
            "execution_enabled": False,
        }
