"""Document 26 (OD-45): E3 Evidence Verification and E4 Source Reliability.

Heuristic grading for Phase 1. Grades are provisional and revisable; no grade
ever turns an interpretation into a fact about a person.
"""

from typing import Any, Dict, List

from app.services.hbi.schemas import EvidenceClass

SOURCE_BASE = {
    "systematic_review": 0.95,
    "meta_analysis": 0.95,
    "peer_reviewed_journal": 0.90,
    "replicated_experiment": 0.92,
    "national_archive": 0.88,
    "primary_source": 0.85,
    "scholarly_book": 0.80,
    "quasi_experiment": 0.75,
    "longitudinal_study": 0.75,
    "survey": 0.60,
    "news": 0.50,
    "public_comment": 0.25,
    "social_media": 0.20,
    "unknown": 0.10,
}


def rate_source(source_type: str, licence: Any = None, permitted_purpose: Any = None,
                learned_weights: Dict[str, Any] = None) -> Dict[str, Any]:
    """Return a reliability rating; empirical calibration overrides the prior when available."""
    base = SOURCE_BASE.get(source_type, SOURCE_BASE["unknown"])
    learned = (learned_weights or {}).get(source_type)
    if learned and learned.get("empirical"):
        base = float(learned["reliability"])
    limitations: List[str] = []
    if learned and learned.get("empirical"):
        limitations.append(f"empirically_calibrated_n={learned['n']}")
    else:
        limitations.append("prior_based_not_empirically_calibrated")
    if not licence:
        base -= 0.15
        limitations.append("licence_not_recorded")
    if not permitted_purpose:
        base -= 0.10
        limitations.append("permitted_purpose_not_recorded")
    if source_type in {"public_comment", "social_media"}:
        limitations.append("not_evidence_of_private_psychological_state")
    return {
        "source_type": source_type,
        "reliability": round(max(0.0, min(1.0, base)), 2),
        "limitations": limitations,
        "grade": "high" if base >= 0.8 else "medium" if base >= 0.55 else "low",
    }


def verify_claim(evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Classify a claim from its evidence set using independent corroboration."""
    if not evidence:
        return {
            "evidence_class": EvidenceClass.UNVERIFIED.value,
            "confidence": 0.0,
            "reason": "no_evidence_supplied",
        }

    ratings = [
        rate_source(item.get("source_type", "unknown"), item.get("licence"), item.get("permitted_purpose"))
        for item in evidence
    ]
    sources = {item.get("source_id") for item in evidence}
    strong = [r for r in ratings if r["reliability"] >= 0.8]
    weak = [r for r in ratings if r["reliability"] < 0.4]
    grades = {item.get("grade") for item in evidence if item.get("grade")}
    has_dispute = any(g in {"conflicted", "disputed", "contested"} for g in grades)

    if has_dispute or (len(strong) >= 1 and len(weak) >= 1):
        evidence_class = EvidenceClass.CONTESTED
        confidence = 0.45
    elif len(strong) >= 2 and len(sources) >= 2:
        evidence_class = EvidenceClass.VERIFIED
        confidence = 0.9
    elif len(strong) >= 1:
        evidence_class = EvidenceClass.WELL_SUPPORTED
        confidence = 0.75
    elif any(r["reliability"] >= 0.55 for r in ratings):
        evidence_class = EvidenceClass.WELL_SUPPORTED
        confidence = 0.6
    else:
        evidence_class = EvidenceClass.UNVERIFIED
        confidence = 0.3

    return {
        "evidence_class": evidence_class.value,
        "confidence": confidence,
        "independent_sources": len(sources),
        "source_ratings": ratings,
        "reason": "provisional_heuristic_grade",
    }
