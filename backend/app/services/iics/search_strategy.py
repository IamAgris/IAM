"""Research strategy selection and confidence calibration (§2.2).

No network access here: deterministic policy the researcher calls before
searching. Hosted providers remain optional; free-first selection is enforced
by PermissionGate and the existing search_service.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

from app.services.iics.source_registry import label_for_confidence

STRATEGIES = (
    "single_query",
    "query_decomposition",
    "source_first",
    "iterative_refinement",
    "contradiction_focused",
)

CONTRADICTION_HINTS = re.compile(
    r"(?i)\b(conflict|contradict|disagree|verify|compare|versus|vs\.?|outdated|rumour|rumor)\b"
)
SUBQUESTION_SPLIT = re.compile(r"\s+(?:and|also|plus|;)\s+|\s*\?\s*")


@dataclass(frozen=True)
class StrategyDecision:
    strategy: str
    rationale: str
    queries: List[str] = field(default_factory=list)
    known_domains: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "rationale": self.rationale,
            "queries": list(self.queries),
            "known_domains": list(self.known_domains),
        }


class StrategySelector:
    """Choose a documented strategy and record the rationale."""

    def select(
        self,
        question: str,
        *,
        known_domains: Optional[List[str]] = None,
        prior_confidence: Optional[float] = None,
        prefer_depth: bool = False,
    ) -> StrategyDecision:
        domains = [d.strip().lower() for d in (known_domains or []) if d.strip()]
        text = (question or "").strip()
        if CONTRADICTION_HINTS.search(text) or (
            prior_confidence is not None and prior_confidence < 0.4
        ):
            return StrategyDecision(
                "contradiction_focused",
                "conflicting or weakly evidenced claim; seek independent sources",
                [text, f"{text} independent sources"],
                domains,
            )
        if domains:
            return StrategyDecision(
                "source_first",
                "trusted domains supplied; retrieve from known authoritative sources",
                [f"site:{domain} {text}" for domain in domains[:5]],
                domains,
            )
        parts = [part.strip() for part in SUBQUESTION_SPLIT.split(text) if part.strip()]
        if len(parts) > 1:
            return StrategyDecision(
                "query_decomposition",
                "question decomposes into sub-questions",
                parts[:8],
                domains,
            )
        if prefer_depth:
            return StrategyDecision(
                "iterative_refinement",
                "depth requested; broaden then refine across passes",
                [text],
                domains,
            )
        return StrategyDecision("single_query", "straightforward factual query", [text], domains)


class ConfidenceCalibrator:
    """Evidence-weighted confidence with a stable, reviewable formula."""

    @staticmethod
    def score(sources: Sequence[Mapping[str, Any]]) -> float:
        """Score in [0,1] from independent corroboration and source quality."""
        if not sources:
            return 0.0
        independent = sum(1 for s in sources if s.get("independent") is True)
        primary = sum(1 for s in sources if s.get("primary") is True)
        reliability = sum(float(s.get("reliability") or 0) for s in sources) / len(sources)
        recency_bonus = 0.1 if any(int(s.get("age_days") or 999) <= 30 for s in sources) else 0.0
        contradictions = sum(1 for s in sources if s.get("contradicts") is True)
        value = 0.25 + 0.15 * min(independent, 3) + 0.10 * min(primary, 2)
        value += 0.25 * max(0.0, min(1.0, reliability))
        value += recency_bonus - 0.20 * min(contradictions, 3)
        return round(max(0.0, min(1.0, value)), 4)

    @staticmethod
    def label(score: float) -> str:
        return label_for_confidence(score)

    @staticmethod
    def sufficient_for_commit(score: float) -> bool:
        return score >= 0.70
