"""Pure IP dispute and incident-response logic (IPLCI P5, IL-15).

An allegation is a claim, not a fact. IAM never automatically accepts an
infringement allegation: it verifies the complainant, preserves evidence,
identifies affected material, restricts only where appropriate, and escalates
legally significant cases.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from app.services.iplci.core import IPLCIError

CASE_TYPES = (
    "copyright", "trademark", "patent", "licence",
    "takedown", "attribution", "ownership",
)
CASE_STATUSES = (
    "received", "verifying", "investigating", "restricted",
    "responded", "resolved", "withdrawn", "appealed",
)
REQUEST_TYPES = (
    "permission", "licence", "renewal", "attribution",
    "dataset_permission", "training_permission",
)
REQUEST_STATUSES = ("requested", "agreed", "rejected", "expired", "withdrawn")


def verify_complainant(claim: Mapping[str, Any]) -> Dict[str, Any]:
    """Verify identity and authority to assert the claimed right."""
    missing = [
        field for field in ("complainant", "identity_ref", "authority_evidence", "asserted_right")
        if not claim.get(field)
    ]
    verified = not missing and bool(claim.get("owner_match") or claim.get("register_match"))
    return {
        "verified": verified,
        "missing": missing,
        "status": "verified" if verified else "unverified",
        "owner_match": bool(claim.get("owner_match")),
        "register_match": bool(claim.get("register_match")),
        "reasons": [
            "Allegations are investigated, not automatically accepted.",
            "Complainant identity and authority must be verified before action beyond preservation.",
        ],
        "policy_version": "5.0",
    }


def assess_dispute(
    case: Mapping[str, Any],
    verification: Mapping[str, Any],
) -> Dict[str, Any]:
    """Decide how to handle a dispute without deciding its merits."""
    case_type = str(case.get("case_type") or "")
    if case_type not in CASE_TYPES:
        raise IPLCIError("IPLCI_INVALID_INPUT", "invalid case_type")

    risk = "MODERATE"
    actions: List[str] = ["preserve evidence and logs", "identify affected assets, datasets and models"]
    if not verification.get("verified"):
        risk = "UNKNOWN"
        actions.append("restrict to verification-only processing; do not accept the claim")
    if case.get("affected_models") or case.get("affected_datasets"):
        risk = "HIGH" if risk != "UNKNOWN" else risk
        actions.append("trace affected training datasets and model versions")
    if case_type in ("patent", "ownership"):
        actions.append("obtain qualified professional review")
    if case.get("deadline"):
        actions.append("record and monitor the response deadline")
    if risk in ("HIGH", "CRITICAL"):
        actions.append("temporarily restrict disputed material where appropriate")
    actions.append("prepare a documented response with supporting evidence")

    return {
        "domain": "ip_dispute",
        "case_type": case_type,
        "risk": risk,
        "outcome": "investigate" if not verification.get("verified") else "investigate_and_respond",
        "accepted_allegation": False,
        "required_actions": actions,
        "professional_review_required": case_type in ("patent", "ownership"),
        "reasons": [
            "A complaint is not proof of infringement; investigation precedes any concession.",
        ],
        "policy_version": "5.0",
    }


def remediation_steps(incident: Mapping[str, Any]) -> List[str]:
    """The ten-step incident-response procedure from the master specification."""
    steps = [
        "stop further affected usage",
        "quarantine the relevant material",
        "preserve evidence and logs",
        "identify all affected projects and model versions",
        "determine the extent of the exposure",
        "assess legal and contractual notification requirements",
        "identify corrective actions",
        "obtain appropriate legal review",
        "document the resolution",
        "update the compliance rules to prevent recurrence",
    ]
    if incident.get("disclosure_type") in ("trade_secret", "confidential", "personal_data"):
        steps.insert(5, "assess accidental disclosure notification duties")
    return steps
