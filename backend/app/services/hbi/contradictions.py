"""Document 26 (OD-45): E11 Contradiction Detection.

Finds conflicting claims and interpretations without silently choosing one.
Contradictions are preserved as evidence, never resolved by fiat.
"""

import re
from typing import Any, Dict, List

_NEGATION = re.compile(r"\b(not|no|never|does not|do not|did not|fails? to|cannot|isn't|aren't)\b", re.I)
_INCREASE = re.compile(r"\b(increase[sd]?|raise[sd]?|improve[sd]?|more|higher)\b", re.I)
_DECREASE = re.compile(r"\b(decrease[sd]?|reduce[sd]?|lower|less|worse)\b", re.I)
_CAUSES = re.compile(r"\b(causes?|leads? to|drives?|produces?)\b", re.I)


def _direction(text: str) -> str:
    if _DECREASE.search(text):
        return "negative"
    if _INCREASE.search(text):
        return "positive"
    return "neutral"


def detect(claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare claims pairwise and report possible conflicts."""
    findings: List[Dict[str, Any]] = []
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            a = str(claims[i].get("claim", ""))
            b = str(claims[j].get("claim", ""))
            reasons = []
            da, db = _direction(a), _direction(b)
            if {da, db} == {"positive", "negative"}:
                reasons.append("opposite_directional_effect")
            na, nb = bool(_NEGATION.search(a)), bool(_NEGATION.search(b))
            if na != nb and (_CAUSES.search(a) or _CAUSES.search(b)):
                reasons.append("negated_causal_claim")
            if reasons:
                findings.append({
                    "claim_a_ref": claims[i].get("record_id", f"index_{i}"),
                    "claim_b_ref": claims[j].get("record_id", f"index_{j}"),
                    "claim_a": a,
                    "claim_b": b,
                    "reasons": reasons,
                    "severity": "high" if len(reasons) > 1 else "medium",
                    "resolution": "unresolved",
                })
    return {
        "contradictions": findings,
        "count": len(findings),
        "note": "Both claims are preserved; no interpretation is silently promoted.",
    }
