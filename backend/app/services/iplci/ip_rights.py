"""Pure trademark, patent and design-right signal logic (IPLCI P2, IL-02…04).

These functions rank *risk and uncertainty* for human/legal review. A similarity
score is never an infringement verdict, a patent search is never a freedom-to-
operate opinion, and an absent register record is never proof of clearance.
"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from app.services.iplci.core import IPLCIError, parse_datetime

RISK_LEVELS = ("LOW", "MODERATE", "HIGH", "CRITICAL", "UNKNOWN")

TRADEMARK_STATUSES = ("registered", "pending", "unregistered", "withdrawn", "expired")
USE_CONTEXTS = (
    "legitimate_reference", "comparative", "ownership_claim",
    "brand_use", "endorsement_claim",
)
PATENT_STATUSES = ("active", "granted", "pending", "expired", "lapsed", "withdrawn")
INFRINGEMENT_ACTIVITIES = ("implement", "make", "use", "sell", "import")
STUDY_ACTIVITIES = ("study", "research", "analyse", "analysis", "read")
DESIGN_RIGHT_TYPES = (
    "industrial_design", "unregistered_design", "geographical_indication",
    "plant_variety", "semiconductor_layout", "domain_name",
)

_RISK_ORDER = {level: index for index, level in enumerate(RISK_LEVELS)}


def _risk(maximum: str, *candidates: str) -> str:
    """Combine risk signals by taking the strongest (most severe) one."""
    return max((maximum, *candidates), key=lambda level: _RISK_ORDER.get(level, 0))


def normalise(text: str) -> str:
    """Normalise a mark/name for comparison without changing its meaning."""
    value = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def tokens(text: str) -> set[str]:
    return {token for token in normalise(text).split() if len(token) > 2}


def similarity(left: str, right: str) -> float:
    """Hybrid character/token similarity in [0, 1]. A signal, not a verdict."""
    a, b = normalise(left), normalise(right)
    if not a or not b:
        return 0.0
    character = SequenceMatcher(None, a, b).ratio()
    ta, tb = tokens(a), tokens(b)
    token = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return round(max(character, token), 4)


def _active(mark: Mapping[str, Any], now: Optional[str] = None) -> bool:
    status = str(mark.get("status") or "unregistered").lower()
    if status in ("expired", "withdrawn"):
        return False
    expiry = parse_datetime(mark.get("expires_at"))
    moment = parse_datetime(now)
    return not (expiry and moment and expiry < moment)


def check_trademark(
    proposed: str,
    marks: Iterable[Mapping[str, Any]],
    *,
    jurisdiction: Optional[str] = None,
    classes: Sequence[str] = (),
    use_context: str = "brand_use",
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """Screen a proposed name for conflicting registered/pending marks."""
    if not str(proposed or "").strip():
        raise IPLCIError("IPLCI_INVALID_INPUT", "proposed name is required")
    if use_context not in USE_CONTEXTS:
        raise IPLCIError("IPLCI_INVALID_INPUT", "invalid use_context")

    wanted = {str(item).upper() for item in classes}
    conflicts: List[Dict[str, Any]] = []
    risk = "LOW"
    for mark in marks or ():
        if not _active(mark, now):
            continue
        mark_classes = {str(item).upper() for item in (mark.get("classes") or [])}
        class_overlap = bool(wanted & mark_classes) if wanted else True
        territories = {str(item).upper() for item in (mark.get("territory") or [])}
        territory_ok = (
            not jurisdiction or not territories or jurisdiction.upper() in territories
        )
        score = similarity(proposed, str(mark.get("mark_text") or ""))
        if score < 0.55 or not class_overlap or not territory_ok:
            continue
        status = str(mark.get("status") or "unregistered").lower()
        status_risk = "UNKNOWN" if status == "pending" else "MODERATE"
        if score >= 0.85:
            status_risk = _risk(status_risk, "HIGH")
        if score >= 0.85 and status == "registered":
            status_risk = "CRITICAL"
        conflicts.append({
            "mark_id": mark.get("id"),
            "mark_text": mark.get("mark_text"),
            "owner": mark.get("owner"),
            "status": status,
            "classes": sorted(mark_classes),
            "similarity": score,
            "risk": status_risk,
        })
        risk = _risk(risk, status_risk)

    if use_context == "legitimate_reference" and risk != "UNKNOWN":
        # Nominative/reference use lowers infringement risk but never licenses
        # ownership claims or implied endorsement.
        risk = RISK_LEVELS[max(0, _RISK_ORDER[risk] - 1)]
    if use_context in ("ownership_claim", "endorsement_claim") and conflicts:
        risk = _risk(risk, "CRITICAL")

    return {
        "domain": "trademark",
        "subject": proposed,
        "risk": risk,
        "outcome": (
            "no_recorded_conflict" if not conflicts else
            "potential_conflict_review_required" if risk in ("MODERATE", "HIGH", "UNKNOWN") else
            "do_not_adopt_without_clearance"
        ),
        "conflicts": conflicts,
        "use_context": use_context,
        "legitimate_reference": use_context in ("legitimate_reference", "comparative"),
        "professional_review_required": risk in ("HIGH", "CRITICAL", "UNKNOWN"),
        "reasons": [
            "A register search is a risk signal, not a legal clearance opinion.",
            "Similar or confusingly similar names require review in relevant classes and territories.",
            "Reference to an existing brand differs from claiming ownership or endorsement.",
        ],
        "policy_version": "2.0",
    }


def check_patent_fto(
    activity: str,
    implementation: str,
    features: Sequence[str],
    patents: Iterable[Mapping[str, Any]],
    *,
    jurisdiction: Optional[str] = None,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """Screen an implementation against patent claims. Not a legal FTO opinion."""
    activity = str(activity or "").strip().lower()
    if not activity:
        raise IPLCIError("IPLCI_INVALID_INPUT", "activity is required")
    if activity in STUDY_ACTIVITIES:
        return {
            "domain": "patent",
            "activity": activity,
            "risk": "LOW",
            "outcome": "study_permitted",
            "overlaps": [],
            "professional_review_required": False,
            "reasons": [
                "Reading a patent, learning about an invention and discussing it are not infringement.",
                "Risk concerns implementing, making, using, selling or importing claimed technology.",
            ],
            "policy_version": "2.0",
        }
    if activity not in INFRINGEMENT_ACTIVITIES:
        raise IPLCIError("IPLCI_INVALID_INPUT", "invalid activity")

    moment = parse_datetime(now)
    feature_tokens = tokens(" ".join([implementation, *features]))
    if not feature_tokens:
        return {
            "domain": "patent", "activity": activity, "risk": "UNKNOWN",
            "outcome": "insufficient_implementation_detail",
            "overlaps": [], "professional_review_required": True,
            "reasons": ["An implementation description or feature list is required."],
            "policy_version": "2.0",
        }

    overlaps: List[Dict[str, Any]] = []
    risk = "LOW"
    for patent in patents or ():
        status = str(patent.get("status") or "pending").lower()
        expiry = parse_datetime(patent.get("expires_at"))
        if status in ("expired", "lapsed", "withdrawn"):
            continue
        if expiry and moment and expiry < moment:
            continue
        patent_jurisdiction = {str(item).upper() for item in (patent.get("jurisdiction") or [])}
        if jurisdiction and patent_jurisdiction and jurisdiction.upper() not in patent_jurisdiction:
            continue
        claim_tokens = tokens(" ".join(str(item) for item in (patent.get("claims") or [])))
        if not claim_tokens:
            coverage = 0.0
        else:
            coverage = round(len(feature_tokens & claim_tokens) / len(feature_tokens), 4)
        if coverage < 0.15:
            continue
        status_risk = "UNKNOWN" if status == "pending" else "MODERATE"
        if coverage >= 0.5:
            status_risk = _risk(status_risk, "CRITICAL")
        elif coverage >= 0.3:
            status_risk = _risk(status_risk, "HIGH")
        overlaps.append({
            "patent_id": patent.get("id"),
            "publication_number": patent.get("publication_number"),
            "title": patent.get("title"),
            "status": status,
            "claim_coverage": coverage,
            "risk": status_risk,
        })
        risk = _risk(risk, status_risk)

    return {
        "domain": "patent",
        "activity": activity,
        "risk": risk,
        "outcome": (
            "no_claim_overlap_detected" if not overlaps else
            "freedom_to_operate_review_required"
        ),
        "overlaps": overlaps,
        "professional_review_required": risk in ("MODERATE", "HIGH", "CRITICAL", "UNKNOWN"),
        "reasons": [
            "A novelty or patentability search is not interchangeable with freedom to operate.",
            "Only enforceable claims in the relevant jurisdiction create infringement risk.",
            "A freedom-to-operate opinion requires a qualified patent professional.",
        ],
        "policy_version": "2.0",
    }


def check_design(
    subject: str,
    rights: Iterable[Mapping[str, Any]],
    *,
    right_type: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    now: Optional[str] = None,
) -> Dict[str, Any]:
    """Screen a product appearance/name/domain against recorded design rights."""
    if not str(subject or "").strip():
        raise IPLCIError("IPLCI_INVALID_INPUT", "subject is required")
    if right_type and right_type not in DESIGN_RIGHT_TYPES:
        raise IPLCIError("IPLCI_INVALID_INPUT", "invalid right_type")

    moment = parse_datetime(now)
    matches: List[Dict[str, Any]] = []
    risk = "LOW"
    for right in rights or ():
        kind = str(right.get("right_type") or "")
        if right_type and kind != right_type:
            continue
        status = str(right.get("status") or "unregistered").lower()
        expiry = parse_datetime(right.get("expires_at"))
        if status == "expired" or (expiry and moment and expiry < moment):
            continue
        score = similarity(subject, str(right.get("subject") or ""))
        exact_domain = kind == "domain_name" and normalise(subject) == normalise(right.get("subject") or "")
        if score < 0.7 and not exact_domain:
            continue
        match_risk = "UNKNOWN" if status == "unregistered" else "HIGH"
        if exact_domain:
            match_risk = "CRITICAL"
        matches.append({
            "right_id": right.get("id"),
            "right_type": kind,
            "subject": right.get("subject"),
            "owner": right.get("owner"),
            "similarity": score,
            "risk": match_risk,
        })
        risk = _risk(risk, match_risk)

    return {
        "domain": "design_rights",
        "subject": subject,
        "right_type": right_type,
        "risk": risk,
        "outcome": "no_recorded_conflict" if not matches else "design_right_review_required",
        "matches": matches,
        "professional_review_required": risk in ("HIGH", "CRITICAL", "UNKNOWN"),
        "reasons": [
            "Industrial designs, design rights, GIs, plant varieties, semiconductor layouts and domains are protected differently per jurisdiction.",
        ],
        "policy_version": "2.0",
    }
