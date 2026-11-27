"""Pure research-ethics, identity and cross-border transfer logic (IL-19)."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from app.services.iplci.core import IPLCIError

_RISK = {"LOW": 0, "MODERATE": 1, "UNKNOWN": 2, "HIGH": 3, "CRITICAL": 4}


def _risk(*levels: str) -> str:
    return max(levels, key=lambda level: _RISK.get(level, 0))


def assess_research_ethics(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Screen voluntary participant research for ethical safeguards."""
    risk = "LOW"
    requirements: List[str] = []
    if not record.get("informed_consent"):
        risk = "UNKNOWN"
        requirements.append("obtain informed consent")
    if record.get("ethics_review_required") and not record.get("ethics_review_completed"):
        risk = _risk(risk, "CRITICAL")
        requirements.append("complete ethics review")
    if record.get("children") or record.get("vulnerable_participants"):
        risk = _risk(risk, "HIGH")
        requirements.append("apply additional safeguards for vulnerable participants")
    if record.get("deception") and not record.get("deception_justified"):
        risk = _risk(risk, "HIGH")
        requirements.append("justify any deception and provide debriefing")
    if not record.get("withdrawal_process"):
        requirements.append("provide a withdrawal process")
    if not record.get("minimisation_applied"):
        requirements.append("minimise collected information")
    if record.get("harm_risk"):
        risk = _risk(risk, "HIGH")
        requirements.append("document harm mitigation")

    return {
        "domain": "research_ethics",
        "subject": str(record.get("subject") or "research_activity"),
        "risk": risk,
        "outcome": "blocked" if risk in ("CRITICAL", "UNKNOWN") else (
            "conditional" if risk == "HIGH" or requirements else "permitted_with_safeguards"
        ),
        "requirements": requirements,
        "reasons": ["Voluntary participant research requires consent, ethics review and withdrawal rights."],
        "policy_version": "4.0",
    }


def assess_identity_use(flags: Mapping[str, Any]) -> Dict[str, Any]:
    """Detect misuse of IAM, creator or business identities."""
    blockers = [
        name for name in (
            "impersonation", "unauthorised_creator_identity",
            "misleading_endorsement", "unauthorised_brand_use",
        ) if flags.get(name)
    ]
    risk = "CRITICAL" if blockers else "LOW"
    conditions: List[str] = []
    if flags.get("public_statement") and not flags.get("authorised"):
        risk = _risk(risk, "HIGH")
        conditions.append("authorise public statements before publication")
    if flags.get("reference_only") and not blockers:
        conditions.append("keep the reference accurate and non-endorsing")
    return {
        "domain": "identity_protection",
        "subject": str(flags.get("subject") or "identity_use"),
        "risk": risk,
        "outcome": "blocked" if risk == "CRITICAL" else "conditional" if risk != "LOW" else "permitted_with_conditions",
        "blockers": blockers,
        "conditions": conditions,
        "reasons": ["Identity and likeness cannot be used to imply ownership, affiliation or endorsement."],
        "policy_version": "4.0",
    }


def assess_cross_border(transfer: Mapping[str, Any]) -> Dict[str, Any]:
    """Screen an international data transfer and residency obligations."""
    origin = str(transfer.get("origin") or "").upper()[:2]
    destinations = [str(item).upper()[:2] for item in (transfer.get("destinations") or [])]
    mechanism = transfer.get("transfer_mechanism")
    categories = {str(item).lower() for item in (transfer.get("data_categories") or [])}
    sensitive = bool(categories & {"sensitive", "biometric", "voice", "health", "children"})

    risk = "LOW"
    requirements: List[str] = []
    if not mechanism:
        risk = _risk(risk, "HIGH" if not sensitive else "CRITICAL")
        requirements.append("record a lawful international transfer mechanism")
    if transfer.get("residency_required") and any(
        destination != origin for destination in destinations
    ):
        risk = _risk(risk, "CRITICAL")
        requirements.append("data residency obligation prohibits this destination")
    if transfer.get("onward_transfer") and not transfer.get("onward_transfer_controls"):
        risk = _risk(risk, "HIGH")
        requirements.append("control onward transfers")
    if not transfer.get("minimisation_applied"):
        requirements.append("apply data minimisation before transfer")

    return {
        "domain": "cross_border_data",
        "origin": origin or None,
        "destinations": destinations,
        "risk": risk,
        "outcome": "blocked" if risk == "CRITICAL" else (
            "conditional" if risk != "LOW" else "permitted_with_conditions"
        ),
        "requirements": requirements,
        "legal_context_status": "requires_verification",
        "reasons": [
            "Cross-border transfers require a lawful mechanism and may be restricted by residency rules.",
        ],
        "policy_version": "4.0",
    }
