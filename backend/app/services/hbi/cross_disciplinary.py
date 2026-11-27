"""Document 26 (OD-45): A6 cross-disciplinary reasoning.

Each discipline contributes separately graded claims. Fusion weights come from
calibration history, not from discipline prestige. Conflicts are preserved and
no single discipline is allowed to dominate by default.
"""

from typing import Any, Dict, List

from app.services.hbi import contradictions

DISCIPLINES = ["psychology", "history", "economics", "neuroscience", "sociology", "communication"]


def fuse(question: str,
         claims_by_discipline: Dict[str, List[Dict[str, Any]]],
         calibration_weights: Dict[str, float] = None) -> Dict[str, Any]:
    contributions = []
    flat = []
    weights = calibration_weights or {d: 1.0 / len(DISCIPLINES) for d in DISCIPLINES}
    total_weight = sum(weights.get(d, 0.0) for d in DISCIPLINES) or 1.0

    for discipline in DISCIPLINES:
        claims = claims_by_discipline.get(discipline, [])
        if not claims:
            continue
        confidence = sum(float(c.get("confidence", 0.0)) for c in claims) / len(claims)
        weight = round(weights.get(discipline, 0.0) / total_weight, 3)
        contributions.append({
            "discipline": discipline,
            "claims": len(claims),
            "mean_confidence": round(confidence, 3),
            "fused_weight": weight,
            "evidence_classes": sorted({c.get("evidence_class", "unverified") for c in claims}),
        })
        flat.extend({"record_id": c.get("record_ref"), "claim": c.get("claim", "")} for c in claims)

    weighted_confidence = round(
        sum(item["mean_confidence"] * item["fused_weight"] for item in contributions), 3
    ) if contributions else 0.0
    dominance = [item["discipline"] for item in contributions if item["fused_weight"] > 0.5]
    conflicts = contradictions.detect(flat)
    return {
        "question": question,
        "contributions": contributions,
        "weighted_confidence": weighted_confidence,
        "single_discipline_dominance": dominance,
        "contradictions": conflicts,
        "status": "cross_disciplinary_interpretation",
        "caveat": "Fusion combines graded claims; it does not prove a conclusion or describe an individual.",
    }
