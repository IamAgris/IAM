"""Controlled Web3 learning records (proposed Doc 35).

Gap identification, research logs, tool benchmarks and versioned technical notes.
This module never modifies the production model, signing infrastructure, financial
governance or protected core. All records are research artefacts only.
"""

from typing import Any, Dict, List

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag


class Web3LearningService:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_registry_enabled,
            "modifies_production_model": False,
            "modifies_financial_governance": False,
            "modifies_signing_infrastructure": False,
            "sandbox_only": True,
            "promotion_requires_creator_approval": True,
        }

    def identify_gaps(self, capabilities: List[Dict[str, Any]]) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        gaps = [
            {
                "area": item.get("area"),
                "reason": item.get("reason", "unverified"),
            }
            for item in capabilities
            if not item.get("verified", False)
        ]
        return {"gaps": gaps, "count": len(gaps), "autonomous_promotion": False}

    def research_record(
        self,
        *,
        topic: str,
        sources: List[str],
        findings: str,
        confidence: float,
        verification: str = "unverified",
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if not topic or not sources or not findings:
            raise ProviderDenied("topic, sources and findings are required")
        if not 0 <= confidence <= 1:
            raise ProviderDenied("confidence must be between 0 and 1")
        return {
            "topic": topic,
            "sources": list(sources),
            "findings": findings,
            "confidence": confidence,
            "verification": verification,
            "promotion_requires_creator_approval": True,
        }

    def benchmark(
        self, *, tool: str, baseline: Dict[str, float], candidate: Dict[str, float]
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if not baseline or not candidate or set(baseline) != set(candidate):
            raise ProviderDenied("baseline and candidate must have identical metric sets")
        improved = all(candidate[key] <= baseline[key] for key in baseline)
        return {
            "tool": tool,
            "improved": improved,
            "metrics": {key: {"baseline": baseline[key], "candidate": candidate[key]} for key in baseline},
            "adopt": False,
            "note": "Adoption requires the measured-benefit gate and creator approval.",
        }

    def version_note(self, *, subject: str, version: str, body: str) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if not subject or not version or not body:
            raise ProviderDenied("subject, version and body are required")
        return {"subject": subject, "version": version, "body": body, "status": "draft"}
