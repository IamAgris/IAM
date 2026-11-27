"""Pure rights-assessment logic for IP & Legal Intelligence (proposed OD-48).

Phase 1: copyright, licence, ownership and provenance decisions.

This module performs no I/O. It is the authoritative decision logic used by the
engine, the API gateway and the tests. Two rules dominate:

* Access is not permission. Reading/analysing, storing, reproducing, training
  and commercialising are separate rights.
* Unknown is not approval. Missing, unverified or unavailable information
  produces QUARANTINE or BLOCK, never APPROVED.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

POLICY_VERSION = "1.0"

RIGHTS = (
    "read", "analyse", "store", "reproduce", "derive",
    "modify", "distribute", "train", "commercialise", "disclose",
)

OPERATION_TO_RIGHT = {
    "read": "read", "access": "read", "view": "read",
    "analyse": "analyse", "analysis": "analyse",
    "store": "store", "retain": "store", "ingest": "store",
    "reproduce": "reproduce", "copy": "reproduce",
    "derive": "derive", "transform": "derive",
    "modify": "modify",
    "distribute": "distribute", "publish": "distribute", "redistribute": "distribute",
    "train": "train", "fine_tune": "train", "finetune": "train",
    "commercialise": "commercialise", "commercialize": "commercialise",
    "commercial": "commercialise", "sell": "commercialise",
    "disclose": "disclose", "egress": "disclose", "external": "disclose",
}

RIGHTS_STATUSES = (
    "PUBLIC_DOMAIN", "OPEN_LICENCE", "CREATIVE_COMMONS",
    "COMMERCIAL_LICENCE", "COPYRIGHT_PROTECTED", "UNKNOWN_OWNERSHIP",
)

SOURCE_CLASSES = (
    "OPEN_RESEARCH", "REFERENCE_ONLY", "LICENSED_RESEARCH",
    "RESTRICTED_RESEARCH", "CONFIDENTIAL", "UNVERIFIED", "PROHIBITED",
)

PERMITTED = "PERMITTED"
PROHIBITED = "PROHIBITED"
UNKNOWN = "UNKNOWN"

DECISION_CLASSES = ("LOW", "MODERATE", "HIGH", "CRITICAL", "UNKNOWN")

RESULTS = (
    "APPROVED", "CONDITIONAL", "BLOCKED",
    "QUARANTINED", "REVOKED", "EXPIRED",
)

SOURCE_STATES = (
    "NOT_VALIDATED", "APPROVED", "RESTRICTED",
    "QUARANTINED", "REVOKED", "EXPIRED", "BLOCKED",
)

# Default posture by copyright status. These are conservative starting points;
# explicit permission records and source-class overrides refine them.
_STATUS_DEFAULTS: Dict[str, Dict[str, str]] = {
    "PUBLIC_DOMAIN": {right: PERMITTED for right in RIGHTS},
    "OPEN_LICENCE": {right: PERMITTED for right in RIGHTS},
    "CREATIVE_COMMONS": {right: PERMITTED for right in RIGHTS},
    "COMMERCIAL_LICENCE": {
        **{right: PERMITTED for right in ("read", "analyse")},
        **{right: UNKNOWN for right in RIGHTS if right not in ("read", "analyse")},
    },
    "COPYRIGHT_PROTECTED": {
        "read": PERMITTED,          # study and analysis where legally permitted
        "analyse": PERMITTED,
        "store": PROHIBITED,
        "reproduce": PROHIBITED,
        "derive": PROHIBITED,
        "modify": PROHIBITED,
        "distribute": PROHIBITED,
        "train": PROHIBITED,
        "commercialise": PROHIBITED,
        "disclose": UNKNOWN,
    },
    "UNKNOWN_OWNERSHIP": {right: UNKNOWN for right in RIGHTS},
}

_STATUS_CONDITIONS: Dict[str, List[str]] = {
    "PUBLIC_DOMAIN": ["subject to applicable law"],
    "OPEN_LICENCE": ["record licence identifier, version and evidence"],
    "CREATIVE_COMMONS": ["follow attribution and licence conditions"],
    "COMMERCIAL_LICENCE": ["use only within purchased permissions"],
    "COPYRIGHT_PROTECTED": ["study/analysis only where legally permitted"],
    "UNKNOWN_OWNERSHIP": ["ownership must be established before use"],
}

_CLASS_OVERRIDES: Dict[str, Dict[str, str]] = {
    "REFERENCE_ONLY": {
        **{right: PERMITTED for right in ("read", "analyse")},
        **{right: PROHIBITED for right in RIGHTS if right not in ("read", "analyse")},
    },
    "RESTRICTED_RESEARCH": {right: UNKNOWN for right in RIGHTS},
    "CONFIDENTIAL": {right: PROHIBITED for right in RIGHTS},
    "UNVERIFIED": {right: UNKNOWN for right in RIGHTS},
    "PROHIBITED": {right: PROHIBITED for right in RIGHTS},
}

_BLOCKING_CLASSES = ("CONFIDENTIAL", "PROHIBITED", "RESTRICTED_RESEARCH")


class IPLCIError(ValueError):
    """An IPLCI input or governance error with a stable machine code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def parse_datetime(value: Any) -> Optional[datetime]:
    """Accept ISO strings or datetimes; return an aware UTC datetime."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def normalise_operation(operation: str) -> str:
    """Map a requested operation to one of the ten governed rights."""
    key = (operation or "").strip().lower().replace("-", "_").replace(" ", "_")
    if key not in OPERATION_TO_RIGHT:
        raise IPLCIError("IPLCI_UNKNOWN_OPERATION", f"unsupported operation: {operation}")
    return OPERATION_TO_RIGHT[key]


def default_permissions(source: Mapping[str, Any]) -> Dict[str, str]:
    """Derive the initial tri-state posture for a source."""
    status = source.get("rights_status") or "UNKNOWN_OWNERSHIP"
    source_class = source.get("source_class") or "UNVERIFIED"
    if status not in RIGHTS_STATUSES:
        status = "UNKNOWN_OWNERSHIP"
    if source_class not in SOURCE_CLASSES:
        source_class = "UNVERIFIED"

    states = dict(_STATUS_DEFAULTS[status])
    states.update(_CLASS_OVERRIDES.get(source_class, {}))

    flags = source.get("licence_flags") or {}
    if isinstance(flags, Mapping):
        if flags.get("non_commercial"):
            states["commercialise"] = PROHIBITED
        if flags.get("no_derivatives"):
            states["derive"] = PROHIBITED
            states["modify"] = PROHIBITED
    return states


def default_conditions(source: Mapping[str, Any]) -> List[str]:
    """Conditions attached to a default posture."""
    status = source.get("rights_status") or "UNKNOWN_OWNERSHIP"
    source_class = source.get("source_class") or "UNVERIFIED"
    conditions = list(_STATUS_CONDITIONS.get(status, []))
    if source_class == "LICENSED_RESEARCH":
        conditions.append("permission evidence must be recorded")
    if source.get("attribution_required"):
        conditions.append("attribution required")
    flags = source.get("licence_flags") or {}
    if isinstance(flags, Mapping) and flags.get("attribution_required"):
        conditions.append("attribution required")
    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: List[str] = []
    for item in conditions:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def effective_permissions(
    source: Mapping[str, Any],
    permissions: Iterable[Mapping[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """Merge default posture with explicit permission records."""
    states = default_permissions(source)
    conditions = default_conditions(source)
    result: Dict[str, Dict[str, Any]] = {
        right: {"state": states[right], "conditions": list(conditions), "basis": "rights_status"}
        for right in RIGHTS
    }
    for record in permissions or ():
        right = record.get("right")
        if right not in RIGHTS:
            continue
        state = record.get("state")
        if state not in (PERMITTED, PROHIBITED, UNKNOWN):
            state = UNKNOWN
        result[right] = {
            "state": state,
            "conditions": list(record.get("conditions") or []),
            "basis": record.get("basis") or "explicit_permission",
            "evidence_ref": record.get("evidence_ref"),
        }
    return result


def _assessment(
    *,
    decision: str,
    decision_class: str,
    right: str,
    reason: str,
    rules: List[str],
    evidence: List[str],
    rights_evaluated: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    return {
        "decision": decision,
        "decision_class": decision_class,
        "right": right,
        "reason": reason,
        "rules_applied": rules,
        "evidence_refs": [item for item in evidence if item],
        "rights_evaluated": rights_evaluated or {},
        "policy_version": POLICY_VERSION,
    }


def assess(
    source: Optional[Mapping[str, Any]],
    permissions: Iterable[Mapping[str, Any]],
    *,
    operation: str,
    jurisdiction: Optional[str] = None,
    now: Optional[datetime] = None,
    policy_version: str = POLICY_VERSION,
) -> Dict[str, Any]:
    """Evaluate a requested operation against the source's rights posture.

    Fail-closed: any missing, ambiguous or unavailable required permission
    yields QUARANTINED (UNKNOWN), never APPROVED.
    """
    moment = parse_datetime(now) or datetime.now(timezone.utc)
    rules: List[str] = ["rights_status", "source_class", "fail_closed"]

    try:
        right = normalise_operation(operation)
    except IPLCIError as exc:
        result = _assessment(
            decision="BLOCKED", decision_class="UNKNOWN", right="unknown",
            reason=exc.message, rules=rules, evidence=[],
        )
        result["error_code"] = exc.code
        return result

    if not source:
        return _assessment(
            decision="QUARANTINED", decision_class="UNKNOWN", right=right,
            reason="source not registered; unknown rights cannot be approved",
            rules=rules, evidence=[],
        )

    evidence = [str(source.get("permission_evidence") or "")]
    rules.append("source_registered")

    state = source.get("current_permission_state")
    if state in ("REVOKED", "EXPIRED", "BLOCKED"):
        return _assessment(
            decision=state, decision_class="CRITICAL", right=right,
            reason=f"source permission state is {state}", rules=rules, evidence=evidence,
        )

    expiry = parse_datetime(source.get("expiry_date"))
    if expiry and expiry < moment:
        return _assessment(
            decision="EXPIRED", decision_class="HIGH", right=right,
            reason="permission has expired", rules=rules + ["expiry_check"], evidence=evidence,
        )

    if source.get("permission_withdrawn"):
        return _assessment(
            decision="REVOKED", decision_class="CRITICAL", right=right,
            reason="permission has been withdrawn", rules=rules + ["revocation_check"], evidence=evidence,
        )

    territory = source.get("territory")
    if jurisdiction and territory:
        allowed = {str(item).upper() for item in territory}
        if jurisdiction.upper() not in allowed:
            return _assessment(
                decision="BLOCKED", decision_class="HIGH", right=right,
                reason=f"jurisdiction {jurisdiction} is outside permitted territory",
                rules=rules + ["territory_check"], evidence=evidence,
            )
        rules.append("territory_check")

    evaluated = effective_permissions(source, permissions)
    rights_evaluated = {name: record["state"] for name, record in evaluated.items()}
    rules.append("explicit_permissions")

    if source.get("personal_data_present") and not source.get("privacy_lawful_basis"):
        if right not in ("read", "analyse"):
            return _assessment(
                decision="QUARANTINED", decision_class="UNKNOWN", right=right,
                reason="personal data present without a documented lawful basis",
                rules=rules + ["privacy_check"], evidence=evidence,
                rights_evaluated=rights_evaluated,
            )
        rules.append("privacy_check")

    entry = evaluated[right]
    permission_state = entry["state"]
    conditions = list(entry["conditions"])
    if entry.get("evidence_ref"):
        evidence.append(str(entry["evidence_ref"]))

    if permission_state == UNKNOWN:
        return _assessment(
            decision="QUARANTINED", decision_class="UNKNOWN", right=right,
            reason=f"right '{right}' is unknown; missing permission is not approval",
            rules=rules, evidence=evidence, rights_evaluated=rights_evaluated,
        )

    source_class = source.get("source_class") or "UNVERIFIED"
    if permission_state == PROHIBITED:
        decision_class = "CRITICAL" if (
            source.get("rights_status") == "COPYRIGHT_PROTECTED"
            or source_class in _BLOCKING_CLASSES
        ) else "HIGH"
        return _assessment(
            decision="BLOCKED", decision_class=decision_class, right=right,
            reason=f"right '{right}' is prohibited for this source ({entry['basis']})",
            rules=rules, evidence=evidence, rights_evaluated=rights_evaluated,
        )

    decision = "CONDITIONAL" if conditions else "APPROVED"
    decision_class = "MODERATE" if conditions else "LOW"
    result = _assessment(
        decision=decision, decision_class=decision_class, right=right,
        reason=f"right '{right}' is permitted under recorded conditions" if conditions
               else f"right '{right}' is permitted within documented scope",
        rules=rules, evidence=evidence, rights_evaluated=rights_evaluated,
    )
    result["conditions"] = conditions
    result["policy_version"] = policy_version
    return result


def gate_check(
    source: Optional[Mapping[str, Any]],
    permissions: Iterable[Mapping[str, Any]],
    *,
    operation: str,
    jurisdiction: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Pre-execution gate. Any internal failure fails closed."""
    try:
        result = assess(source, permissions, operation=operation, jurisdiction=jurisdiction, now=now)
    except Exception as exc:  # pragma: no cover - defensive boundary
        return {
            "decision": "BLOCKED",
            "decision_class": "UNKNOWN",
            "error_code": "IPLCI_POLICY_UNAVAILABLE",
            "reason": f"rights assessment unavailable: {type(exc).__name__}",
            "policy_version": POLICY_VERSION,
            "audit_event_id": None,
        }
    result["audit_event_id"] = None
    return result


def _canonical(record: Mapping[str, Any]) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def audit_hash(previous_hash: str, record: Mapping[str, Any]) -> str:
    """Hash-chained audit event; tampering with any field breaks the chain."""
    payload = {key: value for key, value in record.items() if key not in ("event_hash",)}
    return hashlib.sha256((previous_hash + _canonical(payload)).encode("utf-8")).hexdigest()


def verify_audit_chain(
    events: Iterable[Mapping[str, Any]],
    genesis_hash: Optional[str] = None,
) -> List[str]:
    """Return IDs of events whose hash chain is broken.

    ``genesis_hash`` seeds the chain for a partial (limited) tail read.
    """
    broken: List[str] = []
    previous = genesis_hash or "0" * 64
    for event in events:
        expected = audit_hash(previous, event)
        if event.get("event_hash") != expected:
            broken.append(str(event.get("id", "unknown")))
        previous = str(event.get("event_hash") or expected)
    return broken
