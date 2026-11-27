"""Pure privacy and data-protection assessment (IPLCI P3, IL-08).

Covers POPIA (ZA), GDPR (EU), UK GDPR and applicable US state privacy laws as
*unverified legal context*. These functions never present a legal conclusion:
every result carries ``legal_context_status: requires_verification`` until a
qualified professional records a reference.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from app.services.iplci.core import IPLCIError

JURISDICTIONS = ("ZA", "EU", "UK", "US")
LAWFUL_BASES = (
    "consent", "contract", "legal_obligation", "vital_interests",
    "public_task", "legitimate_interests", "research_public_interest",
)
SENSITIVE_CATEGORIES = ("sensitive", "children", "biometric", "voice", "health", "financial")
# UNKNOWN sits between MODERATE and HIGH: it fails closed on its own but does
# not erase a known CRITICAL safeguard breach.
_RISK = {"LOW": 0, "MODERATE": 1, "UNKNOWN": 2, "HIGH": 3, "CRITICAL": 4}


def _risk(*levels: str) -> str:
    return max(levels, key=lambda level: _RISK.get(level, 0))


def assess_privacy(
    record: Mapping[str, Any],
    *,
    jurisdiction: str,
    purpose: str = "research",
    operation: str = "analyse",
) -> Dict[str, Any]:
    """Evaluate lawful processing of personal information for one operation."""
    if jurisdiction not in JURISDICTIONS:
        raise IPLCIError("IPLCI_INVALID_JURISDICTION", "unsupported jurisdiction")

    if not record.get("personal_data_present"):
        return {
            "domain": "privacy",
            "jurisdiction": jurisdiction,
            "risk": "LOW",
            "outcome": "not_personal_data",
            "requirements": [],
            "legal_context_status": "requires_verification",
            "reasons": ["Recorded as containing no personal information."],
            "policy_version": "3.0",
        }

    risk = "LOW"
    requirements: List[str] = []
    basis = str(record.get("lawful_basis") or "")
    if not basis or basis not in LAWFUL_BASES:
        risk = "UNKNOWN"
        requirements.append("document a valid lawful basis for processing")

    categories = {str(item).lower() for item in (record.get("data_categories") or [])}
    enhanced = categories & set(SENSITIVE_CATEGORIES)
    if enhanced:
        requirements.append("explicit consent and enhanced safeguards for sensitive information")
        requirements.append("complete a data protection impact assessment")
        if not (record.get("explicit_consent") and record.get("dpia_completed")):
            risk = _risk(risk, "CRITICAL")
        if "children" in enhanced:
            requirements.append("additional safeguards for children's information")

    if not record.get("minimisation_applied"):
        risk = _risk(risk, "MODERATE")
        requirements.append("apply data minimisation")
    if not record.get("retention_period"):
        risk = _risk(risk, "MODERATE")
        requirements.append("define a lawful retention period")
    if not record.get("deletion_supported"):
        requirements.append("support lawful deletion")

    if record.get("deletion_requested") and not record.get("deletion_completed"):
        risk = _risk(risk, "HIGH")
        requirements.append("complete the pending deletion request")
    if record.get("dsar_requested") and not record.get("dsar_completed"):
        risk = _risk(risk, "HIGH")
        requirements.append("answer the data subject access request")

    if record.get("international_transfer") and not record.get("transfer_mechanism"):
        risk = _risk(risk, "HIGH")
        requirements.append("record a lawful international transfer mechanism")

    if purpose == "train" and basis == "legitimate_interests":
        risk = _risk(risk, "HIGH")
        requirements.append("complete a balancing assessment before training use")

    if operation in ("disclose", "egress") and not record.get("disclosure_permitted"):
        risk = _risk(risk, "HIGH")
        requirements.append("confirm disclosure to external parties is permitted")

    if risk == "UNKNOWN":
        outcome = "quarantined"
    elif risk in ("CRITICAL", "HIGH"):
        outcome = "blocked_pending_review"
    elif risk == "MODERATE":
        outcome = "conditional_processing"
    else:
        outcome = "permitted_with_safeguards"

    return {
        "domain": "privacy",
        "jurisdiction": jurisdiction,
        "purpose": purpose,
        "operation": operation,
        "risk": risk,
        "outcome": outcome,
        "lawful_basis": basis or None,
        "requirements": requirements,
        "legal_context_status": "requires_verification",
        "reasons": [
            "Public visibility is not legal availability for every form of processing.",
            "Jurisdiction-specific law must be verified against official sources before reliance.",
        ],
        "policy_version": "3.0",
    }
