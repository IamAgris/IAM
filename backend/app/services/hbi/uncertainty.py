"""Document 26 (OD-45): A8 full uncertainty intelligence.

Recognises when human behaviour cannot reliably be predicted and returns a
structured refusal with the evidence that would change the verdict.
"""

from typing import Any, Dict, List


def assess(records: List[Dict[str, Any]], gap_result: Dict[str, Any],
           contradiction_result: Dict[str, Any], scope: str = "aggregate",
           validation: Dict[str, Any] = None) -> Dict[str, Any]:
    conditions: List[Dict[str, str]] = []

    if not records:
        conditions.append({"condition": "no_evidence", "severity": "high"})
    gap_count = len(gap_result.get("gaps", []))
    if gap_count >= 8:
        conditions.append({"condition": "insufficient_evidence", "severity": "high"})
    elif gap_count >= 3:
        conditions.append({"condition": "partial_context", "severity": "medium"})
    if contradiction_result.get("count", 0) >= 2:
        conditions.append({"condition": "contested_interpretations", "severity": "high"})
    if any(r.get("evidence_class") in {"unverified", "speculation"} for r in records):
        conditions.append({"condition": "unverified_sources", "severity": "medium"})
    if scope == "individual":
        conditions.append({"condition": "sensitive_individual_scope", "severity": "high"})
    if validation and not validation.get("validated"):
        conditions.append({"condition": "unvalidated_model", "severity": "high"})

    high = [item for item in conditions if item["severity"] == "high"]
    medium = [item for item in conditions if item["severity"] == "medium"]
    if high:
        verdict = "unreliable"
    elif medium:
        verdict = "conditional"
    else:
        verdict = "reliable"

    result = {
        "verdict": verdict,
        "conditions": conditions,
        "record_count": len(records),
        "what_would_change": [
            "verified independent evidence",
            "fewer unresolved contradictions",
            "recorded context dimensions",
            "validated model with calibration evidence",
        ],
        "note": "Refusing to predict is a successful outcome, not a failure.",
    }
    if verdict == "unreliable":
        result["refusal"] = {
            "code": "A8_UNRELIABLE_PREDICTION_CONTEXT",
            "reason": "human_behaviour_cannot_be_reliably_predicted_here",
            "conditions": high,
        }
    return result
