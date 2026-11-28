"""Recurring scored internet QA with a regression stop-gate (§2.9).

Existing model QA (OD-38/OD-46) is untouched. This suite covers egress,
extraction, source attribution and legal-gate behaviour. No benchmark alone
promotes a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Tuple

Runner = Callable[[], float | Awaitable[float]]


@dataclass(frozen=True)
class BenchmarkCase:
    """A named scored check with a minimum passing threshold."""

    name: str
    threshold: float
    runner: Runner
    evidence: Optional[Mapping[str, Any]] = None


class BenchmarkSuite:
    """Run cases and compare against a previous baseline."""

    def __init__(self, cases: List[BenchmarkCase]) -> None:
        self.cases = cases

    async def run(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for case in self.cases:
            value = case.runner()
            if hasattr(value, "__await__"):
                value = await value
            score = float(value)
            if not 0.0 <= score <= 1.0:
                score = 0.0 if score < 0 else 1.0
            results.append(
                {
                    "benchmark": case.name,
                    "score": score,
                    "threshold": case.threshold,
                    "passed": score >= case.threshold,
                    "evidence": dict(case.evidence or {}),
                }
            )
        return results

    @staticmethod
    def regression_gate(
        baseline: Mapping[str, float],
        current: Mapping[str, float],
        max_drop: float = 0.05,
    ) -> Tuple[bool, List[str]]:
        """Fail if a scored benchmark regresses more than the allowed drop."""
        regressions: List[str] = []
        for name, previous in baseline.items():
            present = current.get(name)
            if present is None:
                regressions.append(f"{name}: missing")
            elif present + max_drop < previous:
                regressions.append(f"{name}: {present:.3f} < {previous:.3f}")
        return (not regressions), regressions
