"""Pure AI-training legal governance logic (IPLCI P3, IL-10).

A source approved for analysis is not approved for training. Training approval
must be independent of the ingestion reviewer, and a licence for a foundation
model does not automatically grant commercial, modification or redistribution
rights. Deleting a dataset does not remove its influence from a trained model.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

from app.services.iplci import core, software

# UNKNOWN is uncertainty, not the highest severity: a known CRITICAL blocker
# must outrank it, while UNKNOWN alone still fails closed.
_RISK = {"LOW": 0, "MODERATE": 1, "UNKNOWN": 2, "HIGH": 3, "CRITICAL": 4}


def _risk(*levels: str) -> str:
    return max(levels, key=lambda level: _RISK.get(level, 0))


def assess_training(
    source: Optional[Mapping[str, Any]],
    permissions: Iterable[Mapping[str, Any]],
    *,
    dataset: Mapping[str, Any],
    approval: Optional[Mapping[str, Any]],
    jurisdiction: Optional[str] = None,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """Combine copyright rights, provenance and independent approval."""
    moment = core.parse_datetime(now) or datetime.now(timezone.utc)
    rights = core.assess(
        source, permissions, operation="train",
        jurisdiction=jurisdiction or dataset.get("jurisdiction"), now=moment,
    )
    reasons: List[str] = []
    conditions: List[str] = list(rights.get("conditions") or [])
    missing: List[str] = []

    if rights.get("decision") not in ("APPROVED", "CONDITIONAL"):
        missing.append("recorded training rights")
        reasons.append(f"rights assessment returned {rights.get('decision')}")

    for field in ("lawfully_obtained", "provenance_recorded"):
        if not dataset.get(field):
            missing.append(field)
    if not dataset.get("rights_assessment_ids"):
        missing.append("linked rights assessments")

    if not approval or str(approval.get("decision") or "").lower() != "approved":
        missing.append("independent training approval")
    else:
        if str(approval.get("approver") or "") == str(approval.get("ingestion_reviewer") or ""):
            missing.append("independent approver (approval must differ from ingestion reviewer)")
        if not approval.get("basis"):
            missing.append("approval basis")

    if dataset.get("personal_data_present") and not dataset.get("privacy_lawful_basis"):
        missing.append("privacy lawful basis for training")

    if dataset.get("approval_expiry"):
        expiry = core.parse_datetime(dataset["approval_expiry"])
        if expiry and expiry < moment:
            missing.append("unexpired approval")

    if missing:
        return {
            "domain": "ai_training",
            "eligible": False,
            "risk": "CRITICAL" if "recorded training rights" in missing or "independent training approval" in missing else "HIGH",
            "outcome": "blocked",
            "missing": missing,
            "conditions": conditions,
            "rights_decision": rights.get("decision"),
            "rights_evaluated": rights.get("rights_evaluated", {}),
            "reasons": reasons or ["training requires all documented permissions and independent approval"],
            "policy_version": "3.0",
        }

    return {
        "domain": "ai_training",
        "eligible": True,
        "risk": "MODERATE" if conditions else "LOW",
        "outcome": "approved_for_training",
        "missing": [],
        "conditions": conditions,
        "rights_decision": rights.get("decision"),
        "rights_evaluated": rights.get("rights_evaluated", {}),
        "reasons": ["Training rights, provenance and independent approval are recorded."],
        "policy_version": "3.0",
    }


def assess_foundation_model(
    model_id: str,
    licence_id: Optional[str],
    *,
    commercial: bool = False,
    modify: bool = False,
    redistribute: bool = False,
) -> Dict[str, Any]:
    """Check a foundation model's licence before deployment or fine-tuning."""
    result = software.check_dependency(
        licence_id,
        distribution="commercial_product" if commercial else "research",
        modification=modify,
    )
    risk = result["risk"]
    conditions = list(result["conditions"])
    if redistribute and result["compatibility"] not in ("COMPATIBLE", "CONDITIONAL"):
        risk = _risk(risk, "CRITICAL")
        conditions.append("redistribution rights must be verified separately")
    if result["compatibility"] == "UNKNOWN":
        risk = _risk(risk, "UNKNOWN")
    return {
        "domain": "ai_training",
        "subject": model_id,
        "risk": risk,
        "outcome": "model_licence_review_required" if risk != "LOW" else "permitted",
        "licence": licence_id,
        "conditions": conditions,
        "reasons": result["reasons"],
        "policy_version": "3.0",
    }


def assess_provider(flags: Mapping[str, Any]) -> Dict[str, Any]:
    """Check external AI provider terms before submitting data."""
    risk = "LOW"
    conditions: List[str] = []
    blockers = [
        name for name in (
            "retains_prompts_without_permission",
            "uses_submissions_for_training",
            "output_ownership_unclear",
            "international_transfer_unauthorised",
            "terms_do_not_permit_operation",
        ) if flags.get(name)
    ]
    if blockers:
        risk = "CRITICAL"
    if flags.get("confidential_data") and not flags.get("confidential_processing_permitted"):
        risk = _risk(risk, "CRITICAL")
        conditions.append("confidential data cannot be submitted to this provider")
    if flags.get("retains_prompts"):
        risk = _risk(risk, "MODERATE")
        conditions.append("confirm prompt retention period")
    if flags.get("international_transfer") and not flags.get("transfer_mechanism"):
        risk = _risk(risk, "HIGH")
        conditions.append("record a lawful transfer mechanism")
    if not flags.get("terms_verified"):
        risk = _risk(risk, "UNKNOWN")
        conditions.append("verify current provider terms before submission")

    return {
        "domain": "ai_training",
        "subject": str(flags.get("provider") or "external_provider"),
        "risk": risk,
        "outcome": "blocked" if blockers or risk in ("CRITICAL", "UNKNOWN") else "conditional_use",
        "blockers": blockers,
        "conditions": conditions,
        "reasons": ["External AI providers are subordinate tools, not authorities over IAM governance."],
        "policy_version": "3.0",
    }


def check_lineage(
    base_model: Mapping[str, Any],
    dataset_ids: Iterable[str],
    dataset_states: Mapping[str, str],
) -> Dict[str, Any]:
    """Determine whether revoked/expired datasets affect a trained model."""
    affected = [
        str(dataset_id) for dataset_id in dataset_ids
        if str(dataset_states.get(str(dataset_id)) or "NOT_VALIDATED").upper()
        in ("REVOKED", "EXPIRED", "BLOCKED", "QUARANTINED")
    ]
    return {
        "domain": "ai_training",
        "model_id": base_model.get("model_id"),
        "risk": "CRITICAL" if affected else "LOW",
        "outcome": "remediation_required" if affected else "lineage_intact",
        "affected_dataset_ids": affected,
        "deletion_is_not_untraining": True,
        "reasons": [
            "Removing a dataset does not automatically remove its influence from an already-trained model.",
        ],
        "policy_version": "3.0",
    }
