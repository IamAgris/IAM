"""Query-level live evidence cache and reputation annotation (proposed Doc 32 §7).

Freshness TTL by class. Source reputation is read from the existing IICS source
registry — no duplicate reputation table, no vector database, no trusted-knowledge
write. Cache failures never break research: callers fail soft.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.iics import IICSSource
from app.models.live_evidence import LiveEvidenceCache
from app.services.live_information_policy import LiveEvidence

TTL_MINUTES = {
    "breaking": 15,
    "current": 60,
    "standard": 360,
    "stable": 60 * 24 * 30,
}


def freshness_class(trigger: Any) -> str:
    categories = tuple(getattr(trigger, "categories", ()) or ())
    if "breaking_news" in categories:
        return "breaking"
    if any(
        name in categories
        for name in (
            "latest_news",
            "current_events",
            "latest_technology",
            "current_prices",
            "company_developments",
            "current_laws",
            "sports_results",
            "weather",
            "live_information",
            "explicit_search",
        )
    ):
        return "current"
    return "standard"


def query_hash(query: str) -> str:
    return hashlib.sha256((query or "").strip().lower().encode("utf-8")).hexdigest()


async def get_cached(db: AsyncSession, query: str) -> Optional[LiveEvidence]:
    """Return unexpired cached evidence, or None. Never raises."""
    try:
        row = (
            await db.execute(
                select(LiveEvidenceCache).where(
                    LiveEvidenceCache.query_hash == query_hash(query)
                )
            )
        ).scalar_one_or_none()
        if not row:
            return None
        now = datetime.now(timezone.utc)
        expires = row.expires_at
        if expires and expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if not expires or expires <= now:
            return None
        await db.execute(
            update(LiveEvidenceCache)
            .where(LiveEvidenceCache.id == row.id)
            .values(hit_count=LiveEvidenceCache.hit_count + 1)
        )
        await db.commit()
        return LiveEvidence(
            query=str(row.query),
            retrieved_at=row.retrieved_at.isoformat() if row.retrieved_at else "",
            provider=str(row.provider or "unavailable") + "+cache",
            results=list(row.results or []),
            errors=list(row.errors or []),
        )
    except Exception:  # pragma: no cover - cache must never break research
        return None


async def store_cached(
    db: AsyncSession, evidence: LiveEvidence, trigger: Any
) -> None:
    """Persist a bounded evidence record with a class TTL. Never raises."""
    try:
        category = freshness_class(trigger)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=TTL_MINUTES[category])
        digest = query_hash(evidence.query)
        row = (
            await db.execute(
                select(LiveEvidenceCache).where(LiveEvidenceCache.query_hash == digest)
            )
        ).scalar_one_or_none()
        if row:
            row = cast(Any, row)
            row.results = evidence.results
            row.errors = evidence.errors
            row.provider = evidence.provider
            row.retrieved_at = now
            row.expires_at = expires
            row.freshness_class = category
        else:
            db.add(
                LiveEvidenceCache(
                    query_hash=digest,
                    query=evidence.query,
                    provider=evidence.provider,
                    results=evidence.results,
                    errors=evidence.errors,
                    freshness_class=category,
                    retrieved_at=now,
                    expires_at=expires,
                )
            )
        await db.commit()
    except Exception:  # pragma: no cover - cache must never break research
        try:
            await db.rollback()
        except Exception:
            pass


async def annotate_reputation(
    db: AsyncSession, results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Attach IICS reliability/freshness signals. Signals are not permission gates."""
    if not results:
        return results
    try:
        domains = {item.get("source") or "" for item in results if item.get("source")}
        if not domains:
            return results
        rows = (await db.execute(select(IICSSource))).scalars().all()
        by_domain = {
            str(row.domain).lower(): row
            for row in rows
            if row.revoked_at is None and row.domain
        }
        for item in results:
            source = by_domain.get(str(item.get("source") or "").lower())
            item["reliability"] = (
                round(float(source.reliability_score), 4) if source else 0.0
            )
            item["source_freshness_class"] = (
                str(source.freshness_class) if source else "unknown"
            )
    except Exception:  # pragma: no cover - reputation must never break research
        for item in results:
            item.setdefault("reliability", 0.0)
    return results
