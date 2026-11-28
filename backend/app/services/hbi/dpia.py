"""Document 26 (OD-45): structured DPIA input for HBI.

This is a technical input for an authorised reviewer, not legal clearance
or a clinical/consequential decision.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List


def sign_off(reviewer: str, decision: str, basis: str) -> Dict[str, Any]:
    """Record an authorised reviewer's DPIA decision."""
    if not reviewer or not basis:
        raise ValueError("reviewer_and_basis_required")
    if decision not in {"approved", "rejected"}:
        raise ValueError("invalid_decision")
    return {
        "reviewer": reviewer,
        "decision": decision,
        "basis": basis,
        "signed_at": datetime.now(timezone.utc).isoformat(),
        "note": "Technical sign-off; not a legal clearance.",
    }


def build(service: Any) -> Dict[str, Any]:
    purposes = sorted({event.get("purpose", "") for event in service.core.audit_log if event.get("purpose")})
    data_categories = [
        {"tier": "T0", "description": "public licensed research"},
        {"tier": "T1", "description": "curated verified findings"},
        {"tier": "T2", "description": "anonymised aggregate patterns"},
        {"tier": "T3", "description": "consented individual interaction data — restricted"},
    ]
    risks = [
        {"risk": "sensitive_trait_inference", "likelihood": "low", "impact": "high",
         "control": "prohibited_marker_gate_and_tier_separation"},
        {"risk": "cultural_generalisation", "likelihood": "medium", "impact": "medium",
         "control": "cultural_context_engine_and_anti_generalisation_caveats"},
        {"risk": "misuse_for_manipulation", "likelihood": "medium", "impact": "high",
         "control": "defensive_only_dual_use_review_and_safety_stop"},
        {"risk": "unreliable_prediction_used_as_fact", "likelihood": "medium", "impact": "high",
         "control": "A8_uncertainty_gate_probability_confidence_separation"},
        {"risk": "unauthorised_individual_profiling", "likelihood": "low", "impact": "high",
         "control": "no_scraped_profiles_scope_gate_human_oversight"},
    ]
    return {
        "system": "IAM Human Behaviour Intelligence",
        "document": "26",
        "status": "technical_input_for_authorised_reviewer",
        "purposes_observed": purposes,
        "data_categories": data_categories,
        "legal_frameworks": {
            "South_Africa": "POPIA — minimisation, purpose limitation, consent, retention, data-subject rights",
            "European_Union": "GDPR + applicable AI regulation — special-category restrictions, DPIA, human oversight",
            "emotion_recognition": "heightened restrictions; not used for employment, financial or access decisions",
        },
        "risks": risks,
        "controls": [
            "tier_separation", "purpose_limitation", "consent_management", "encryption",
            "access_control", "audit_logging", "retention_and_deletion", "dual_use_review",
            "human_oversight_gate", "safety_stop",
        ],
        "residual_risk": "medium_pending_reviewer_signoff",
        "review_due": "before_production_deployment",
        "note": "Not legal advice and not a clearance; the authorised reviewer must sign off.",
    }
