"""Document 26 (OD-45): causal discipline helpers.

Correlation is never promoted to causation. Quasi-experimental estimates carry
their identification assumptions and are reported as conditional.
"""

from typing import Any, Dict, List

_ASSUMPTIONS = [
    "parallel_trends", "no_spillover", "no_simultaneous_shock",
    "consistent_measurement", "no_selection_on_outcome",
]


def difference_in_differences(treatment_pre: float, treatment_post: float,
                              control_pre: float, control_post: float) -> Dict[str, Any]:
    effect = (treatment_post - treatment_pre) - (control_post - control_pre)
    return {
        "estimate": round(effect, 4),
        "method": "difference_in_differences",
        "identification": "conditional",
        "assumptions": list(_ASSUMPTIONS),
        "note": "Estimate holds only if the stated assumptions are defensible.",
    }


def causal_assessment(question: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Report whether causal language is permitted for a question."""
    causal = [
        r for r in records
        if r.get("causal_status") == "causal"
        and r.get("evidence_class") in {"verified", "well_supported"}
    ]
    correlational = [r for r in records if r.get("causal_status") == "correlational"]
    if not causal:
        return {
            "question": question,
            "causal_status": "correlational",
            "permitted_language": "associated_with",
            "refusal": {
                "code": "CAUSAL_EVIDENCE_INSUFFICIENT",
                "reason": "no_verified_causal_identification_for_this_question",
            },
            "correlational_records": len(correlational),
        }
    return {
        "question": question,
        "causal_status": "causal",
        "permitted_language": "estimated_effect_under_stated_assumptions",
        "supporting_records": [r["record_ref"] for r in causal],
        "assumptions_required": list(_ASSUMPTIONS),
        "note": "Causal claims are conditional on design and assumptions, never automatic.",
    }
