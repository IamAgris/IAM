"""Pure jurisdiction resolution and applicable-law mapping (CE-03, IL-13).

Law entries are owner-supplied context for investigation, not legal conclusions.
Every returned provision is marked ``requires_verification`` until a qualified
professional records a reference against an official source.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from app.services.iplci.core import IPLCIError

# Context only — verify current text and commencement against official sources.
JURISDICTION_LAW: Dict[str, Dict[str, List[str]]] = {
    "ZA": {
        "privacy": ["POPIA"],
        "ip": ["Copyright Act", "Trade Marks Act", "Patents Act"],
        "consumer": ["Consumer Protection Act"],
        "corporate": ["Companies Act", "CIPC registers"],
    },
    "EU": {
        "privacy": ["GDPR"],
        "ip": ["copyright directives", "EU trademark and patent frameworks"],
        "ai": ["AI Act"],
        "platform": ["Digital Services Act"],
    },
    "UK": {
        "privacy": ["UK GDPR", "Data Protection Act"],
        "ip": ["Copyright, Designs and Patents Act", "UK trademark and patent legislation"],
    },
    "US": {
        "privacy": ["applicable state privacy laws"],
        "ip": ["Copyright Act", "Lanham Act", "Patent Act", "DMCA"],
    },
}

OFFICIAL_AUTHORITIES = (
    "CIPC", "WIPO", "EUIPO", "USPTO", "UK_IPO", "SA_GOVERNMENT",
    "EURLEX", "COURT", "LEGISLATURE", "REGULATOR",
)


def resolve_jurisdictions(
    *,
    origin: Optional[str] = None,
    processing_locations: Iterable[str] = (),
    target_markets: Iterable[str] = (),
    establishment: Optional[str] = None,
) -> Dict[str, Any]:
    """Derive relevant jurisdictions from origin, processing and markets."""
    candidates: List[str] = []
    for value in (origin, establishment, *processing_locations, *target_markets):
        if not value:
            continue
        key = str(value).strip().upper()[:2]
        if key and key not in candidates:
            candidates.append(key)

    unknown = [item for item in candidates if item not in JURISDICTION_LAW]
    known = [item for item in candidates if item in JURISDICTION_LAW]
    primary = next((item for item in (origin, establishment) if item and str(item).upper()[:2] in known), None)
    if not primary and known:
        primary = known[0]

    return {
        "domain": "jurisdiction",
        "jurisdictions": known,
        "unresolved_jurisdictions": unknown,
        "primary": str(primary).upper()[:2] if primary else None,
        "multiple_jurisdictions": len(known) > 1,
        "escalation_required": bool(unknown) or len(known) > 1,
        "legal_context_status": "requires_verification",
        "reasons": [
            "Relevance is determined by data origin, processing locations, target markets and establishment.",
            "Conflicting requirements between jurisdictions require escalation, not silent selection.",
        ],
        "policy_version": "4.0",
    }


def applicable_law(jurisdictions: Iterable[str], domain: str) -> List[Dict[str, str]]:
    """List contextual legal provisions for a jurisdiction/domain pair."""
    result: List[Dict[str, str]] = []
    for jurisdiction in jurisdictions:
        key = str(jurisdiction).upper()[:2]
        for provision in JURISDICTION_LAW.get(key, {}).get(domain, []):
            result.append({
                "jurisdiction": key,
                "domain": domain,
                "provision": provision,
                "status": "requires_verification",
            })
    return result


def check_territory(
    permission_territory: Optional[Iterable[str]],
    jurisdictions: Iterable[str],
) -> Dict[str, Any]:
    """Check permitted territory against resolved jurisdictions."""
    allowed = {str(item).upper() for item in (permission_territory or [])}
    requested = {str(item).upper()[:2] for item in jurisdictions}
    if not allowed:
        return {"permitted": False, "status": "UNKNOWN", "missing": list(requested)}
    missing = sorted(requested - allowed)
    return {
        "permitted": not missing,
        "status": "PERMITTED" if not missing else "PROHIBITED",
        "missing": missing,
    }


def verify_official_source(source: Mapping[str, Any]) -> Dict[str, Any]:
    """Check whether a legal source record is fit to support a conclusion."""
    authority = str(source.get("authority") or "")
    required = ("authority", "jurisdiction", "url", "provision_ref", "document_type")
    missing = [field for field in required if not source.get(field)]
    problems: List[str] = []
    if authority not in OFFICIAL_AUTHORITIES:
        problems.append("authority is not on the official-source allow-list")
    if source.get("document_type") in ("bill", "draft", "policy", "guidance"):
        problems.append("document is not binding law; label it accordingly")
    if source.get("prediction"):
        problems.append("prediction must never be presented as enacted law")

    if missing or problems:
        status = "unverified"
    elif not source.get("verified_by"):
        status = "requires_verification"
    else:
        status = "verified"

    return {
        "domain": "legal_knowledge",
        "authority": authority,
        "status": status,
        "missing_fields": missing,
        "problems": problems,
        "verified_by": source.get("verified_by"),
        "verified_at": source.get("verified_at"),
        "last_checked_at": source.get("last_checked_at"),
        "reasons": ["Conclusions must link to the actual official provision they rely on."],
        "policy_version": "4.0",
    }


def assess_legal_change(change: Mapping[str, Any]) -> Dict[str, Any]:
    """Classify a monitored legal change for impact assessment."""
    kind = str(change.get("document_type") or "announcement")
    if kind not in (
        "constitution", "legislation", "regulation", "court_judgment", "guidance",
        "policy", "bill", "draft", "treaty", "standard", "announcement",
    ):
        raise IPLCIError("IPLCI_INVALID_INPUT", "invalid document_type")
    binding = kind in ("constitution", "legislation", "regulation", "court_judgment", "treaty")
    if change.get("prediction"):
        binding = False
    priority = "critical" if change.get("affects_legal_operation") else (
        "important" if change.get("effective_date") else "informational"
    )
    return {
        "domain": "legal_change",
        "document_type": kind,
        "binding": binding,
        "priority": priority,
        "effective_date": change.get("effective_date"),
        "transitional_provisions": bool(change.get("transitional_provisions")),
        "label": "prediction" if change.get("prediction") else (
            "enacted_or_binding" if binding else "non_binding_context"
        ),
        "reasons": [
            "Bills, drafts, guidance and predictions do not carry the same authority as enacted law.",
        ],
        "policy_version": "4.0",
    }
