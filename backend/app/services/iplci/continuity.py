"""Pure legal-hold, retention and continuity logic (IPLCI P5, IL-16/20)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

from app.services.iplci.core import parse_datetime


def legal_hold_guard(
    hold: Optional[Mapping[str, Any]],
    evidence: Iterable[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Block deletion of evidence covered by an active legal hold."""
    hold_map = hold or {}
    active = bool(hold_map) and not hold_map.get("released_at")
    blocked: List[str] = []
    scope = set(str(item).upper() for item in (hold_map.get("scope") or []))
    for item in evidence or ():
        if not active:
            break
        asset = str(item.get("asset_id") or "").upper()
        case = str(item.get("case_id") or "").upper()
        if (asset and asset in scope) or (case and case in scope) or item.get("legal_hold_id") == hold_map.get("id"):
            blocked.append(str(item.get("id") or "unknown"))
    return {
        "domain": "legal_hold",
        "hold_active": active,
        "can_delete": not blocked,
        "blocked_evidence_ids": blocked,
        "reasons": [
            "Evidence relevant to an active dispute, investigation or litigation must be preserved.",
        ],
        "policy_version": "5.0",
    }


def retention_decision(
    record: Mapping[str, Any],
    *,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """Decide whether a record may be deleted under its retention schedule."""
    moment = parse_datetime(now) or datetime.now(timezone.utc)
    if record.get("under_legal_hold"):
        return {
            "domain": "records_retention",
            "action": "retain",
            "risk": "HIGH",
            "reasons": ["An active legal hold overrides the retention schedule."],
            "policy_version": "5.0",
        }
    expiry = parse_datetime(record.get("retention_until"))
    if expiry and expiry > moment:
        return {
            "domain": "records_retention",
            "action": "retain",
            "risk": "LOW",
            "reasons": ["Retention period has not expired."],
            "policy_version": "5.0",
        }
    if not expiry:
        return {
            "domain": "records_retention",
            "action": "review",
            "risk": "MODERATE",
            "reasons": ["No retention period is recorded; do not delete by default."],
            "policy_version": "5.0",
        }
    return {
        "domain": "records_retention",
        "action": "delete_if_lawful",
        "risk": "LOW",
        "reasons": ["Retention period expired; confirm no other preservation duty applies."],
        "policy_version": "5.0",
    }


def continuity_check(state: Mapping[str, Any]) -> Dict[str, Any]:
    """Assess whether governance evidence survives failures and model changes."""
    problems: List[str] = []
    if not state.get("audit_chain_valid"):
        problems.append("audit hash chain is broken")
    if not state.get("signed_policy_version"):
        problems.append("no signed compliance policy version is available")
    if not state.get("evidence_complete"):
        problems.append("required compliance evidence is missing")
    if state.get("gateway_unavailable"):
        problems.append("policy enforcement gateway is unavailable; fail-closed required")

    actions: List[str] = []
    if problems:
        actions = [
            "restore governance state from signed, tamper-evident evidence",
            "re-run permission checks in fail-closed mode",
            "escalate to human review before resuming affected operations",
        ]
    return {
        "domain": "legal_continuity",
        "risk": "CRITICAL" if problems else "LOW",
        "outcome": "recovery_required" if problems else "governance_intact",
        "problems": problems,
        "recovery_actions": actions,
        "reasons": [
            "Compliance must survive model updates, restarts and infrastructure failures.",
        ],
        "policy_version": "5.0",
    }
