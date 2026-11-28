"""Document 26 (OD-45): module 27 — Historical Civilisation Intelligence.

Studies development, transformation and decline without reducing complex
events to a single cause. Competing explanations are preserved.
"""

from typing import Any, Dict, List

FACTORS = [
    "political_stability", "institutional_trust", "inequality", "resources",
    "leadership", "technology", "social_cohesion", "external_pressure",
    "institutional_adaptation",
]


def analyse(question: str, records: List[Dict[str, Any]], graph: Any) -> Dict[str, Any]:
    civilisations = graph.query(node_type="civilisation")["nodes"]
    societies = graph.query(node_type="society")["nodes"]
    institutions = graph.query(node_type="institution")["nodes"]

    evidence_by_factor = {}
    for factor in FACTORS:
        evidence_by_factor[factor] = [
            {
                "record_ref": r["record_ref"],
                "claim": r["claim"],
                "evidence_class": r["evidence_class"],
            }
            for r in records
            if factor.replace("_", " ") in r["claim"].lower()
            or factor in str((r.get("context_dimensions") or {}).get("environment", {})).lower()
        ][:5]

    explanations: List[Dict[str, Any]] = []
    for factor, evidence in evidence_by_factor.items():
        if evidence:
            explanations.append({
                "factor": factor,
                "status": "candidate_explanation",
                "evidence": evidence,
                "confidence": round(sum(0.8 if e["evidence_class"] == "verified" else 0.4 for e in evidence) / len(evidence), 2),
            })
    explanations.sort(key=lambda item: item["confidence"], reverse=True)

    return {
        "module_id": 27,
        "question": question,
        "civilisations": civilisations,
        "societies": societies,
        "institutions": institutions,
        "factors": FACTORS,
        "candidate_explanations": explanations,
        "single_cause_claim": False,
        "note": "Decline and development are multi-factor; no explanation is treated as final.",
    }
