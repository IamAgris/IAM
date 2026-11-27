"""Pure web-collection legality logic (IPLCI P3, IL-07).

Robots.txt is a crawling signal, never legal permission. Public visibility is
not reuse permission. IAM must not bypass paywalls, authentication, technical
protection measures or access restrictions to obtain information.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from app.services.iplci.core import IPLCIError

# UNKNOWN is uncertainty, not the highest severity.
_RISK = {"LOW": 0, "MODERATE": 1, "UNKNOWN": 2, "HIGH": 3, "CRITICAL": 4}


def _risk(*levels: str) -> str:
    return max(levels, key=lambda level: _RISK.get(level, 0))


def assess_collection(
    flags: Mapping[str, Any],
    *,
    intended_use: str = "research",
) -> Dict[str, Any]:
    """Evaluate a prospective collection operation from source flags."""
    if intended_use not in ("research", "commercial", "redistribution", "training"):
        raise IPLCIError("IPLCI_INVALID_INPUT", "invalid intended_use")

    bypasses = [
        name for name in (
            "bypassed_paywall", "bypassed_authentication",
            "circumvented_tpm", "bypassed_access_control",
        ) if flags.get(name)
    ]
    risk = "LOW"
    conditions: List[str] = []
    reasons: List[str] = []

    if bypasses:
        risk = "CRITICAL"
        reasons.append("collection bypassed a paywall, authentication, access control or technical protection measure")

    robots = str(flags.get("robots_txt") or "absent").lower()
    if robots in ("disallow", "disallowed"):
        risk = _risk(risk, "MODERATE")
        conditions.append("robots.txt disallows this path; treat as a stop signal and obtain permission")

    for flag, label in (
        ("terms_of_service_restricts_collection", "site terms restrict automated collection"),
        ("scraping_restricted", "scraping is restricted"),
        ("automated_collection_restricted", "automated collection is restricted"),
        ("api_terms_restrict_use", "API terms restrict this use"),
    ):
        if flags.get(flag):
            risk = _risk(risk, "HIGH")
            conditions.append(label)

    if flags.get("paywall") or flags.get("login_required") or flags.get("access_control"):
        if not flags.get("permission_evidence"):
            risk = _risk(risk, "HIGH")
            conditions.append("access-restricted material requires documented permission")

    if flags.get("rate_limited") and not flags.get("rate_limits_respected"):
        risk = _risk(risk, "HIGH")
        conditions.append("respect published rate limits")

    if flags.get("database_rights") and intended_use in ("commercial", "redistribution"):
        risk = _risk(risk, "HIGH")
        conditions.append("database rights may restrict extraction or reuse")

    if flags.get("commercial_reuse_restricted") and intended_use in ("commercial", "training"):
        risk = _risk(risk, "HIGH")
        conditions.append("commercial reuse is restricted")

    if flags.get("personal_data"):
        risk = _risk(risk, "MODERATE")
        conditions.append("establish a privacy lawful basis before collection")

    if not reasons:
        reasons.append("No blocking collection signal was recorded; this is not a grant of reuse rights")

    reasons.extend([
        "robots.txt is a crawling signal, not legal permission.",
        "Publicly accessible information is not automatically public domain or reusable.",
    ])

    blocked = bool(bypasses)
    if blocked:
        outcome = "prohibited_collection"
    elif risk in ("HIGH", "CRITICAL", "UNKNOWN"):
        outcome = "additional_approval_required"
    elif risk == "MODERATE":
        outcome = "conditional_collection"
    else:
        outcome = "permitted_with_conditions"

    return {
        "domain": "data_collection",
        "intended_use": intended_use,
        "risk": risk,
        "outcome": outcome,
        "blocked": blocked,
        "bypasses": bypasses,
        "conditions": conditions,
        "reasons": reasons,
        "policy_version": "3.0",
    }
