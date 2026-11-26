"""Remaining white-hat enforcement (WH-03…WH-09).

Study and research never grant executable capability (WH-09), security
operations carry a structured audit record (WH-07), and peer exchange is
restricted to reports/research/signed fixes (WH-06). These are infrastructure
rules, not personality instructions.
"""

import json
from typing import Any, Dict, Iterable

from app.services.security_policy import forbidden_capability

DEFENSIVE_FRAMEWORKS = (
    {"id": "owasp", "name": "OWASP Top 10 / ASVS", "purpose": "defensive vulnerability classes"},
    {"id": "attack", "name": "MITRE ATT&CK", "purpose": "detection and defence mapping"},
    {"id": "d3fend", "name": "MITRE D3FEND", "purpose": "defensive countermeasure mapping"},
    {"id": "nist-csf", "name": "NIST CSF", "purpose": "risk and governance lifecycle"},
    {"id": "cis", "name": "CIS Controls", "purpose": "baseline hardening"},
    {"id": "pentest-methodology", "name": "Authorised penetration-test methodology", "purpose": "scope and rules of engagement"},
    {"id": "secure-coding", "name": "Secure coding", "purpose": "prevent common defects"},
    {"id": "incident-response", "name": "Incident response", "purpose": "detect, contain, recover"},
)

STUDY_POLICY = {
    "learning_only": True,
    "execution_allowed": False,
    "capability_granted": False,
    "offensive_tool_creation": False,
}

SHAREABLE_TOPICS = frozenset(
    {"report", "research", "signed_fix", "finding", "status", "skill_release"}
)
_EXECUTABLE_KEYS = frozenset(
    {"code", "script", "payload", "exploit", "command", "binary", "executable", "implant"}
)


class WhiteHatPolicyError(PermissionError):
    """Raised when a study record or peer payload crosses a defensive boundary."""


def _walk(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item)


def ensure_learning_only(payload: Dict[str, Any]) -> Dict[str, Any]:
    """WH-09: studying a technique must never create an executable capability."""
    capability = forbidden_capability(json.dumps(payload, default=str))
    if capability:
        raise WhiteHatPolicyError(f"prohibited capability in study material: {capability}")
    for key in _walk(payload):
        if isinstance(key, str) and key.lower() in _EXECUTABLE_KEYS:
            raise WhiteHatPolicyError(
                "study records must not contain executable code, scripts or payloads"
            )
    return payload


def ensure_p2p_shareable(topic: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """WH-06: share reports, research and signed fixes — never offensive tools."""
    if topic not in SHAREABLE_TOPICS:
        raise WhiteHatPolicyError(f"topic is not shareable over P2P: {topic}")
    return ensure_learning_only(payload)


def build_security_audit(
    *,
    action: str,
    actor: str,
    target: str,
    scope: Dict[str, Any],
    authority: Dict[str, Any],
    tool_calls: Any,
    approval: Dict[str, Any],
    changes: Any,
) -> Dict[str, Any]:
    """WH-07 canonical detail schema for security operations."""
    return {
        "target": target,
        "scope": scope,
        "authority": authority,
        "tool_calls": tool_calls,
        "approval": approval,
        "changes": changes,
        "action": action,
        "actor": actor,
    }
