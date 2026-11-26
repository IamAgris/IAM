"""Document 26 (OD-45): human oversight gate.

IAM must not independently decide consequential outcomes using behavioural
predictions. It supplies an evidence packet to an authorised human instead.
"""

from typing import Any, Dict

CONSEQUENTIAL = {
    "employment", "financial_eligibility", "access_rights", "safety_status",
    "legal_status", "insurance", "housing", "education_admission",
}


def check(decision_type: str, evidence: Dict[str, Any] = None) -> Dict[str, Any]:
    normalised = decision_type.strip().lower().replace(" ", "_")
    if normalised in CONSEQUENTIAL:
        return {
            "decision_type": normalised,
            "automated_decision_permitted": False,
            "human_review_required": True,
            "evidence_packet": {
                "analysis": (evidence or {}).get("analysis"),
                "probability": (evidence or {}).get("probability", {}),
                "confidence": (evidence or {}).get("confidence"),
                "uncertainty": (evidence or {}).get("uncertainty", {}),
                "alternatives": (evidence or {}).get("alternatives", []),
                "disconfirming_evidence_required": True,
            },
            "note": "Behavioural predictions are advisory only; the human decision-maker remains accountable.",
        }
    return {
        "decision_type": normalised,
        "automated_decision_permitted": False,
        "human_review_required": False,
        "status": "analysis_only",
        "note": "No consequential decision is automated by HBI.",
    }
