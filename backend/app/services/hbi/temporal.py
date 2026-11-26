"""Document 26 (OD-45): E2 Temporal Intelligence Engine.

Tracks how graded behavioural records change over time. A single observation
is never treated as a permanent characteristic.
"""

from collections import Counter
from typing import Any, Dict, List

from app.services.hbi.chronology import _year


def _record_year(record: Dict[str, Any], context_key: str):
    dims = record.get("context_dimensions") or {}
    candidates = [
        dims.get(context_key),
        (dims.get("environment") or {}).get("period"),
        (dims.get("behaviour") or {}).get("observed_at"),
    ]
    for evidence in record.get("evidence") or []:
        candidates.append(evidence.get("collection_date"))
    for candidate in candidates:
        if isinstance(candidate, dict):
            candidate = candidate.get("value") or candidate.get("observed_at")
        year = _year(candidate)
        if year is not None:
            return int(year)
    return None


def analyse(records: List[Dict[str, Any]], question: str = "",
            context_key: str = "time", limit: int = 200) -> Dict[str, Any]:
    dated = []
    undated = 0
    for record in records[:limit]:
        year = _record_year(record, context_key)
        if year is None:
            undated += 1
        else:
            dated.append((year, record))
    if not dated:
        return {
            "question": question,
            "buckets": [],
            "refusal": {
                "code": "INSUFFICIENT_TEMPORAL_EVIDENCE",
                "reason": "no_dated_records_available",
            },
            "note": "A pattern observed once is not a permanent characteristic.",
        }

    counts = Counter(year for year, _ in dated)
    buckets = [{"year": year, "count": counts[year]} for year in sorted(counts)]
    changes = []
    for index in range(1, len(buckets)):
        previous, current = buckets[index - 1]["count"], buckets[index]["count"]
        if previous > 0:
            ratio = round(current / previous, 2)
            if ratio >= 2 or ratio <= 0.5:
                changes.append({
                    "from_year": buckets[index - 1]["year"],
                    "to_year": buckets[index]["year"],
                    "ratio": ratio,
                    "interpretation": "possible_change_point",
                })
    return {
        "question": question,
        "buckets": buckets,
        "dated_records": len(dated),
        "undated_records": undated,
        "change_points": changes,
        "caveat": "Temporal pattern in graded records, not proof of a stable trait or a causal trend.",
    }
