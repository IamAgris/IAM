"""Document 26 (OD-45): dual-use review gate.

Every new HBI capability is classified before deployment. Capability growth
never automatically expands permission.
"""

from typing import Any, Dict, List

PROHIBITED_MARKERS = [
    "influence_content", "targeting", "individual_profile", "sensitive_inference",
    "automated_consequential_decision", "psychological_warfare", "deception",
    "criminality_prediction", "emotion_based_decision",
]
RESTRICTED_MARKERS = [
    "emotion_inference", "aggregate_forecast", "manipulation_detection",
    "historical_group_traits", "individual_interaction", "propaganda_detection",
]
_CONTROLS = {
    "emotion_inference": ["weak_signal_labelling", "no_consequential_use", "cultural_context_required"],
    "aggregate_forecast": ["k_anonymity", "purpose_limitation", "uncertainty_disclosure"],
    "manipulation_detection": ["defensive_use_only", "no_influence_content", "dual_use_review"],
    "historical_group_traits": ["no_transfer_to_living_individuals", "contested_sources_preserved"],
    "individual_interaction": ["consent", "minimisation", "retention_limit", "no_sensitive_inference"],
    "propaganda_detection": ["defensive_use_only", "source_provenance", "audit"],
}


def review(capability: str, markers: List[str], purpose: str,
           scope: str = "aggregate") -> Dict[str, Any]:
    forbidden = [marker for marker in markers if marker in PROHIBITED_MARKERS]
    restricted = [marker for marker in markers if marker in RESTRICTED_MARKERS]
    if scope == "individual" and "individual_interaction" not in markers:
        forbidden.append("unauthorised_individual_scope")
    if forbidden:
        decision = "PROHIBITED"
        controls = ["do_not_deploy", "redesign_required"]
    elif restricted:
        decision = "RESTRICTED"
        controls = sorted({control for marker in restricted for control in _CONTROLS.get(marker, [])})
    else:
        decision = "PERMITTED"
        controls = ["standard_governance", "audit"]
    return {
        "capability": capability,
        "purpose": purpose,
        "scope": scope,
        "decision": decision,
        "prohibited_markers": forbidden,
        "restricted_markers": restricted,
        "required_controls": controls,
        "note": "A restricted capability is not approved for deployment until controls are verified.",
    }
