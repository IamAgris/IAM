"""Document 26 (OD-45): empirical calibration of source reliability.

Heuristic source grades are priors. With enough labelled outcomes, a Beta-
smoothed empirical success rate replaces the prior; otherwise the prior stays.
"""

from collections import defaultdict
from typing import Any, Dict, List


def learn_source_weights(cases: List[Dict[str, Any]], min_n: int = 3) -> Dict[str, Dict[str, Any]]:
    """Learn per-source-type reliability from labelled, licensed outcomes."""
    groups: Any = defaultdict(lambda: {"n": 0, "successes": 0})
    for case in cases:
        source_type = str(case.get("source_type") or "unknown")
        groups[source_type]["n"] += 1
        groups[source_type]["successes"] += int(case.get("outcome", 0))
    learned = {}
    for source_type, values in groups.items():
        n, successes = values["n"], values["successes"]
        posterior = (1.0 + successes) / (2.0 + n)
        learned[source_type] = {
            "reliability": round(posterior, 3),
            "n": n,
            "empirical": n >= min_n,
            "successes": successes,
        }
    return learned
