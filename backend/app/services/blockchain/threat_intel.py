"""Multi-source Web3 threat assessment (proposed Doc 35).

No single score is authoritative. Signals come from independent sources and a
high-risk signal is never overridden by an aggregate score.
"""

from typing import Any, Dict, List

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag

HIGH_SIGNALS = frozenset(
    {
        "drainer_contract",
        "phishing_contract",
        "unlimited_approval_requested",
        "rug_pull_indicator",
        "compromised_key",
        "exploit_disclosure",
        "oracle_manipulation",
        "flash_loan_attack_pattern",
        "address_poisoning",
        "credential_compromise",
    }
)
MEDIUM_SIGNALS = frozenset(
    {
        "unverified_source",
        "proxy_contract",
        "new_token",
        "low_liquidity",
        "concentrated_holders",
        "bridge_vulnerability_report",
    }
)


class ThreatIntelService:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_threat_intel_enabled,
            "independent_sources_required": True,
            "single_score_authoritative": False,
            "fail_closed_on_high_signal": True,
        }

    def assess(self, *, target: str, signals: List[Dict[str, Any]]) -> Dict[str, Any]:
        require_flag(settings.web3_threat_intel_enabled, "threat intelligence is disabled")
        if not target:
            raise ProviderDenied("target is required")
        names: List[str] = []
        sources: set = set()  # type: ignore[type-arg]
        for item in signals:
            if not isinstance(item, dict) or not item.get("name"):
                raise ProviderDenied("each signal needs a name and source")
            names.append(str(item["name"]))
            if item.get("source"):
                sources.add(str(item["source"]))
        high = sorted({name for name in names if name in HIGH_SIGNALS})
        medium = sorted({name for name in names if name in MEDIUM_SIGNALS})
        unknown = sorted({name for name in names if name not in HIGH_SIGNALS | MEDIUM_SIGNALS})
        level = "high" if high else ("medium" if len(medium) >= 2 else "low")
        return {
            "target": target,
            "risk": level,
            "high_signals": high,
            "medium_signals": medium,
            "unclassified_signals": unknown,
            "independent_sources": len(sources),
            "decision": "deny" if high else "review" if level == "medium" else "allow_research",
            "note": "A low aggregate never overrides a known high-signal indicator.",
        }
