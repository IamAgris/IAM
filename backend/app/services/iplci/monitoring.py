"""Pure compliance monitoring and deadline logic (IPLCI P5, IL-16)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

from app.services.iplci.core import parse_datetime

DEADLINE_TYPES = (
    "filing", "renewal", "reporting", "retention", "dispute",
    "registration", "review", "deletion",
)
DEADLINE_STATUSES = ("upcoming", "due", "overdue", "completed")


def detect_permission_changes(
    sources: Iterable[Mapping[str, Any]],
    *,
    now: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Detect expired or revoked permissions requiring reassessment."""
    moment = parse_datetime(now) or datetime.now(timezone.utc)
    changes: List[Dict[str, Any]] = []
    for source in sources or ():
        state = str(source.get("current_permission_state") or "").upper()
        expiry = parse_datetime(source.get("expiry_date"))
        if state in ("REVOKED", "BLOCKED") or source.get("permission_withdrawn"):
            changes.append({
                "source_id": source.get("id"),
                "change": "revoked",
                "risk": "CRITICAL",
            })
        elif expiry and expiry < moment:
            changes.append({
                "source_id": source.get("id"),
                "change": "expired",
                "risk": "HIGH",
            })
    return changes


def reassessment_trigger(event: Mapping[str, Any]) -> Dict[str, Any]:
    """Decide whether a legal/licence change requires a fresh assessment."""
    triggers = []
    for field, label in (
        ("licence_changed", "licence terms changed"),
        ("law_changed", "applicable law changed"),
        ("ownership_changed", "ownership changed"),
        ("permission_revoked", "permission withdrawn"),
        ("jurisdiction_changed", "jurisdiction changed"),
    ):
        if event.get(field):
            triggers.append(label)
    return {
        "domain": "compliance_monitoring",
        "required": bool(triggers),
        "triggers": triggers,
        "risk": "HIGH" if triggers else "LOW",
        "outcome": "reassess" if triggers else "no_change_detected",
        "reasons": [
            "Past assessments do not remain valid when licences, laws or ownership change.",
        ],
        "policy_version": "5.0",
    }


def deadline_state(deadline: Mapping[str, Any], *, now: Optional[str] = None) -> str:
    """Return upcoming/due/overdue/completed for one deadline."""
    if str(deadline.get("status") or "").lower() in ("completed", "cancelled"):
        return "completed"
    due = parse_datetime(deadline.get("due_at"))
    if not due:
        return "upcoming"
    moment = parse_datetime(now) or datetime.now(timezone.utc)
    days = (due - moment).total_seconds() / 86400
    if days < 0:
        return "overdue"
    if days <= 7:
        return "due"
    return "upcoming"


def compliance_calendar(
    deadlines: Iterable[Mapping[str, Any]],
    *,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a prioritised compliance calendar with creator alerts."""
    items: List[Dict[str, Any]] = []
    for deadline in deadlines or ():
        kind = str(deadline.get("deadline_type") or "review")
        if kind not in DEADLINE_TYPES:
            continue
        state = deadline_state(deadline, now=now)
        items.append({
            "deadline_id": deadline.get("id"),
            "deadline_type": kind,
            "due_at": deadline.get("due_at"),
            "state": state,
            "jurisdiction": deadline.get("jurisdiction"),
            "proof_ref": deadline.get("proof_ref"),
            "alert": state in ("due", "overdue"),
        })
    items.sort(key=lambda item: str(item.get("due_at") or ""))
    return {
        "domain": "compliance_calendar",
        "items": items,
        "alerts": [item for item in items if item["alert"]],
        "overdue": [item for item in items if item["state"] == "overdue"],
        "policy_version": "5.0",
    }
