"""Document 26 (OD-45): E13 Historical Chronology Engine.

Handles uncertain dates, overlapping timelines and conflicting accounts.
It never forces a single linear narrative where evidence does not support one.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

_YEAR_RE = re.compile(r"(-?\d{1,6})")
_PRECISION_WIDEN = {"millennium": 500, "century": 50, "decade": 5, "year": 0, "month": 0, "day": 0}


def _year(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    match = _YEAR_RE.search(text)
    return float(match.group(1)) if match else None


def date_bounds(date_value: Any) -> Optional[Tuple[float, float]]:
    """Return an approximate [low, high] year range, preserving uncertainty."""
    if date_value is None:
        return None
    if isinstance(date_value, (str, int, float)):
        years = [float(y) for y in _YEAR_RE.findall(str(date_value))]
        if not years:
            return None
        return (min(years), max(years))

    value = date_value.get("value") if isinstance(date_value, dict) else None
    years = [float(y) for y in _YEAR_RE.findall(str(value))] if value is not None else []
    low = _year(date_value.get("earliest")) if isinstance(date_value, dict) else None
    high = _year(date_value.get("latest")) if isinstance(date_value, dict) else None
    if low is None and years:
        low = min(years)
    if high is None and years:
        high = max(years)
    if low is None or high is None:
        return None
    widen = _PRECISION_WIDEN.get(str(date_value.get("precision", "year")).lower(), 0)
    return (low - widen, high + widen)


def _event_bounds(event: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    date = event.get("date")
    if isinstance(date, dict) and ("start" in date or "end" in date):
        starts = date_bounds(date.get("start"))
        ends = date_bounds(date.get("end"))
        if starts and ends:
            return (min(starts[0], ends[0]), max(starts[1], ends[1]))
        return starts or ends
    return date_bounds(date)


def resolve(events: List[Dict[str, Any]],
            uncertain_periods: Optional[List[Dict[str, Any]]] = None,
            conflicting_accounts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Order events by approximate date while retaining overlaps and conflicts."""
    resolved = []
    for event in events:
        bounds = _event_bounds(event)
        resolved.append({
            "event_id": event.get("event_id") or event.get("name") or f"event_{len(resolved)}",
            "name": event.get("name"),
            "bounds": list(bounds) if bounds else None,
            "calendar": (event.get("date") or {}).get("calendar") if isinstance(event.get("date"), dict) else None,
            "precision": (event.get("date") or {}).get("precision") if isinstance(event.get("date"), dict) else None,
            "date_confidence": (event.get("date") or {}).get("confidence") if isinstance(event.get("date"), dict) else None,
            "undated": bounds is None,
        })

    dated = [item for item in resolved if item["bounds"]]
    dated.sort(key=lambda item: item["bounds"][0])
    relations = []
    for i in range(len(dated)):
        for j in range(i + 1, len(dated)):
            a, b = dated[i], dated[j]
            a0, a1 = a["bounds"]
            b0, b1 = b["bounds"]
            if a1 >= b0:
                relation = "overlaps" if not (a1 <= b0 or b1 <= a0) else "concurrent"
                if a0 == b0 and a1 == b1:
                    relation = "concurrent"
            else:
                relation = "before"
            confidence = None
            if a["date_confidence"] is not None and b["date_confidence"] is not None:
                confidence = round(min(float(a["date_confidence"]), float(b["date_confidence"])), 2)
            relations.append({
                "event_a": a["event_id"], "event_b": b["event_id"],
                "relation": relation, "relation_confidence": confidence,
            })

    return {
        "ordered_events": dated + [item for item in resolved if item["undated"]],
        "relations": relations,
        "uncertain_periods": uncertain_periods or [],
        "conflicting_accounts": conflicting_accounts or [],
        "note": "Uncertain and undated material is retained, not discarded or forced into order.",
    }
