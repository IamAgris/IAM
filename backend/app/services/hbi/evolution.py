"""Document 26 (OD-45): A7 knowledge evolution.

Revisions are immutable versions with rationale; old claims remain queryable
and contested interpretations are never silently collapsed.
"""

from typing import Any, Dict, Optional


async def revise(store: Any, old_ref: str, payload: Any, rationale: str) -> Dict[str, Any]:
    """Create a new version and mark the old one superseded."""
    if not rationale:
        raise ValueError("rationale_required")
    new_record = await store.add(payload)
    link = store.supersede(old_ref, new_record["record_ref"], rationale)
    return {
        **link,
        "rationale": rationale,
        "old_claim": store.get(old_ref)["claim"],
        "new_claim": new_record["claim"],
        "note": "Previous version retained and queryable.",
    }


def deprecate(store: Any, record_ref: str, reason: str) -> Dict[str, Any]:
    _typed_result: dict[str, Any] = store.deprecate(record_ref, reason)
    return _typed_result


def lineage(store: Any, record_ref: str) -> Dict[str, Any]:
    chain = store.lineage(record_ref)
    return {"chain": chain, "length": len(chain)}
