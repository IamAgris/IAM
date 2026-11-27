"""Document 26 (OD-45): E12 Knowledge Gap Detection.

Reports what HBI does not yet understand, so A1 self-directed research has a
legitimate trigger. A gap is not an invitation to guess.
"""

from collections import Counter
from typing import Any, Dict, List

CONTEXT_DIMENSIONS = [
    "individual", "context", "environment", "emotion", "motivation",
    "cognition", "experience", "social_influence", "behaviour", "outcome",
]

DIVISION_MODULE_IDS = {
    "D1_human_psychology": [1, 2, 3, 4, 24, 25],
    "D2_motivation_decisions": [5, 6, 7, 29, 30, 34],
    "D3_communication_social": [8, 9, 10, 31, 32, 37],
    "D4_collective_cultural": [11, 12, 26, 28, 33, 35, 36, 38],
    "D5_historical": [16, 17, 18, 19, 20, 21, 22, 23, 27],
    "D6_prediction_learning": [13, 14, 15],
}


def detect(records: List[Dict[str, Any]], query: str = "") -> Dict[str, Any]:
    covered = Counter()
    modules = Counter()
    evidence_classes = Counter()
    for record in records:
        for dim in (record.get("context_dimensions") or {}):
            covered[dim] += 1
        for module_id in record.get("module_ids") or []:
            modules[module_id] += 1
        if record.get("evidence_class"):
            evidence_classes[record["evidence_class"]] += 1

    missing_dimensions = [d for d in CONTEXT_DIMENSIONS if covered[d] == 0]
    thin_divisions = []
    for division, ids in DIVISION_MODULE_IDS.items():
        if not any(modules[mid] > 0 for mid in ids):
            thin_divisions.append(division)

    gaps = []
    if not records:
        gaps.append("no_behavioural_knowledge_records")
    for dim in missing_dimensions:
        gaps.append(f"context_dimension::{dim}")
    for division in thin_divisions:
        gaps.append(f"division::{division}")
    if evidence_classes["contested"] and not evidence_classes["verified"]:
        gaps.append("no_verified_evidence_for_contested_area")

    return {
        "query": query,
        "records_analysed": len(records),
        "gaps": gaps,
        "coverage": {d: covered[d] for d in CONTEXT_DIMENSIONS},
        "research_triggers": [
            {"gap": g, "action": "A1_self_directed_research", "status": "candidate"}
            for g in gaps[:10]
        ],
        "note": "Gaps are research candidates, never justification for speculation.",
    }
