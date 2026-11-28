"""Pure software-IP and licence-compatibility logic (IPLCI P2, IL-09).

Licence compliance is evaluated separately from vulnerability status: a secure
dependency can still be legally incompatible, and a legally clean dependency
can still be vulnerable. Unknown licence information is never approval.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from app.services.iplci.core import IPLCIError

DISTRIBUTIONS = ("internal", "commercial_product", "redistribute", "saas", "research")
SOURCE_ORIGINS = (
    "original", "third_party", "ai_generated", "copied_public",
    "generated_from_licensed_model", "employment_or_contractor", "unclear",
)

# A compact, versioned rule set. SPDX IDs are normalised; complex compound
# expressions deliberately resolve to UNKNOWN and require review.
LICENCE_RULES: Dict[str, Dict[str, Any]] = {
    "mit": {"category": "permissive", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": None},
    "apache-2.0": {"category": "permissive", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": None, "patent_grant": True},
    "bsd-2-clause": {"category": "permissive", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": None},
    "bsd-3-clause": {"category": "permissive", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": None},
    "isc": {"category": "permissive", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": None},
    "gpl-2.0": {"category": "strong_copyleft", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": "strong"},
    "gpl-3.0": {"category": "strong_copyleft", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": "strong"},
    "agpl-3.0": {"category": "network_copyleft", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": "network"},
    "lgpl-2.1": {"category": "weak_copyleft", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": "weak"},
    "lgpl-3.0": {"category": "weak_copyleft", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": "weak"},
    "mpl-2.0": {"category": "weak_copyleft", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": "file"},
    "epl-2.0": {"category": "weak_copyleft", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": "weak"},
    "cc-by-4.0": {"category": "creative_commons", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": None},
    "cc-by-sa-4.0": {"category": "creative_commons", "commercial": True, "modification": True, "redistribution": True, "attribution": True, "copyleft": "share_alike"},
    "cc-by-nc-4.0": {"category": "creative_commons", "commercial": False, "modification": True, "redistribution": True, "attribution": True, "copyleft": None},
    "proprietary": {"category": "proprietary", "commercial": False, "modification": False, "redistribution": False, "attribution": True, "copyleft": None},
    "source-available": {"category": "source_available", "commercial": False, "modification": False, "redistribution": False, "attribution": True, "copyleft": None},
}

_ALIASES = {
    "mit license": "mit", "apache 2.0": "apache-2.0", "apache 2": "apache-2.0",
    "apache-2": "apache-2.0", "bsd": "bsd-3-clause", "gpl-3.0-only": "gpl-3.0",
    "gpl-3.0-or-later": "gpl-3.0", "gpl-2.0-only": "gpl-2.0",
    "agpl-3.0-only": "agpl-3.0", "lgpl-3.0-only": "lgpl-3.0",
    "cc-by-nc": "cc-by-nc-4.0", "cc-by-sa": "cc-by-sa-4.0", "cc-by": "cc-by-4.0",
}


def normalise_licence(value: Optional[str]) -> str:
    """Resolve a licence label to a rule key; compound/unknown stays unknown."""
    raw = str(value or "").strip().lower().replace("_", "-")
    if not raw or raw in ("none", "unknown", "unlicensed", "noassertion"):
        return "unknown"
    if " or " in raw or " and " in raw or "(" in raw:
        return "compound"
    key = _ALIASES.get(raw, raw)
    return key if key in LICENCE_RULES else "unknown"


def check_dependency(
    licence_id: Optional[str],
    *,
    distribution: str,
    project_licence: Optional[str] = None,
    modification: bool = False,
    network_service: bool = False,
    vulnerability_status: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate one dependency's licence compatibility for an intended use."""
    if distribution not in DISTRIBUTIONS:
        raise IPLCIError("IPLCI_INVALID_INPUT", "invalid distribution")
    key = normalise_licence(licence_id)
    rule = LICENCE_RULES.get(key)
    conditions: List[str] = []
    reasons: List[str] = []

    if rule is None:
        return {
            "domain": "software_ip",
            "licence": licence_id,
            "normalised_licence": key,
            "compatibility": "UNKNOWN",
            "risk": "UNKNOWN",
            "conditions": ["obtain and verify the actual licence text before use"],
            "reasons": ["Unknown or compound licences are never approval."],
            "vulnerability_tracked_separately": True,
            "policy_version": "2.0",
        }

    category = str(rule["category"])
    copyleft = rule.get("copyleft")
    risk = "LOW"
    compatibility = "COMPATIBLE"

    if rule.get("attribution"):
        conditions.append("retain licence text and attribution notices")
    if modification and rule.get("modification"):
        conditions.append("mark modified files where required")

    commercial = distribution in ("commercial_product", "redistribute", "saas")
    if commercial and not rule.get("commercial"):
        compatibility = "INCOMPATIBLE"
        risk = "CRITICAL"
        reasons.append("licence does not permit the intended commercial use")
    elif copyleft == "strong" and distribution in ("commercial_product", "redistribute"):
        project_key = normalise_licence(project_licence)
        if project_key != key:
            compatibility = "INCOMPATIBLE"
            risk = "CRITICAL"
            reasons.append("strong copyleft is incompatible with a different distributed project licence")
        else:
            conditions.append("distribute corresponding source under the same licence")
            risk = "MODERATE"
            compatibility = "CONDITIONAL"
    elif copyleft == "network" and network_service and distribution == "saas":
        compatibility = "INCOMPATIBLE"
        risk = "CRITICAL"
        reasons.append("network copyleft obligations apply to network services")
    elif copyleft in ("weak", "file"):
        conditions.append("isolate modifications and honour weak-copyleft obligations")
        if distribution in ("commercial_product", "redistribute"):
            risk = "MODERATE"
            compatibility = "CONDITIONAL"
    elif copyleft == "share_alike":
        conditions.append("share-alike obligations apply to derivatives")
        risk = "MODERATE"
        compatibility = "CONDITIONAL"

    if category in ("proprietary", "source_available") and not commercial:
        risk = "MODERATE"
        compatibility = "CONDITIONAL"
        reasons.append("proprietary/source-available terms must be confirmed for this use")

    if not reasons:
        reasons.append(f"{key} permits the intended {distribution} use subject to recorded conditions")

    return {
        "domain": "software_ip",
        "licence": licence_id,
        "normalised_licence": key,
        "category": category,
        "compatibility": compatibility,
        "risk": risk,
        "conditions": conditions,
        "reasons": reasons,
        "vulnerability_status": vulnerability_status,
        "vulnerability_tracked_separately": True,
        "policy_version": "2.0",
    }


def check_source_origin(origin: str, *, third_party_licence: Optional[str] = None) -> Dict[str, Any]:
    """Classify source-code ownership uncertainty (IL-09 §3.2)."""
    if origin not in SOURCE_ORIGINS:
        raise IPLCIError("IPLCI_INVALID_INPUT", "invalid origin")
    review = origin in ("unclear", "copied_public", "generated_from_licensed_model")
    if origin == "third_party" and not third_party_licence:
        review = True
    return {
        "domain": "software_ip",
        "origin": origin,
        "risk": "HIGH" if review else "LOW",
        "review_required": review,
        "conditions": (
            ["establish ownership or licence before inclusion"] if review else
            ["record origin in the project ownership register"]
        ),
        "reasons": [
            "Original, third-party, AI-generated, copied and unclear code have different ownership consequences.",
            "IAM must not assume it owns everything it creates.",
        ],
        "policy_version": "2.0",
    }


def summarise_sbom(components: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """Summarise a bill of materials; licence and vulnerability views stay distinct."""
    items = list(components or [])
    licence_counts: Dict[str, int] = {}
    unresolved: List[str] = []
    copyleft: List[str] = []
    vulnerable: List[str] = []
    for item in items:
        key = normalise_licence(item.get("licence_id"))
        licence_counts[key] = licence_counts.get(key, 0) + 1
        if key in ("unknown", "compound"):
            unresolved.append(str(item.get("name") or "unnamed"))
        rule = LICENCE_RULES.get(key)
        if rule and rule.get("copyleft"):
            copyleft.append(str(item.get("name") or "unnamed"))
        status = str(item.get("vulnerability_status") or "").lower()
        if status in ("critical", "high"):
            vulnerable.append(str(item.get("name") or "unnamed"))
    return {
        "domain": "software_ip",
        "component_count": len(items),
        "licence_counts": licence_counts,
        "unresolved_licences": unresolved,
        "copyleft_components": copyleft,
        "high_vulnerability_components": vulnerable,
        "licence_compliance_separate_from_vulnerabilities": True,
        "policy_version": "2.0",
    }
