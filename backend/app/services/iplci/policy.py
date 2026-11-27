"""Signed, versioned IPLCI compliance policies (P6).

Policies are tamper-evident records, not model state. IAM cannot relax a
safeguard or disable enforcement through its own reasoning, sub-agents,
plugins or self-improvement; any relaxation requires separate human approval.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Mapping, Optional

PROTECTED_RULES = (
    "access_is_not_permission",
    "unknown_never_approved",
    "mandatory_gateway",
    "fail_closed",
    "no_self_modification",
    "human_approval_for_binding_actions",
)


class PolicyError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# Only these fields are signed; storage metadata (id, created_at, payload,
# approval reference) must not invalidate an otherwise intact signature.
SIGNED_FIELDS = ("version", "rules", "signed_by", "signed_at", "status")


def policy_hash(document: Mapping[str, Any]) -> str:
    payload = {key: document.get(key) for key in SIGNED_FIELDS}
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


def sign_policy(
    rules: Mapping[str, Any],
    *,
    version: str,
    signed_by: str,
    signed_at: str,
) -> Dict[str, Any]:
    """Create a signed policy document. ``signed_by`` must be a human authority."""
    if not version or not signed_by:
        raise PolicyError("IPLCI_POLICY_INVALID", "version and signed_by are required")
    document: Dict[str, Any] = {
        "version": version,
        "rules": dict(rules),
        "signed_by": signed_by,
        "signed_at": signed_at,
        "status": "active",
    }
    document["signature"] = policy_hash(document)
    return document


def verify_policy(document: Optional[Mapping[str, Any]]) -> bool:
    """Verify signature hash and presence of all protected safeguards."""
    if not document:
        return False
    if document.get("signature") != policy_hash(document):
        return False
    if str(document.get("status")) != "active":
        return False
    rules = document.get("rules") or {}
    return all(bool(rules.get(rule)) for rule in PROTECTED_RULES)


def check_relaxation(
    current: Mapping[str, Any],
    proposed: Mapping[str, Any],
    *,
    human_approval_reference: Optional[str] = None,
) -> Dict[str, Any]:
    """Reject any attempt to weaken a protected safeguard without human approval."""
    removed: list[str] = []
    for rule in PROTECTED_RULES:
        was = bool((current.get("rules") or {}).get(rule))
        now = bool((proposed.get("rules") or {}).get(rule))
        if was and not now:
            removed.append(rule)
    if (removed or str(proposed.get("status")) != "active") and not human_approval_reference:
        return {
            "permitted": False,
            "removed_safeguards": removed,
            "error_code": "IPLCI_POLICY_IMMUTABLE",
            "reason": "Legal safeguards cannot be changed without authorised human approval",
        }
    return {"permitted": True, "removed_safeguards": removed}
