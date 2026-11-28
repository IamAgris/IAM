"""Contextual suggestions and public memory nodes for the IAM interface.

Public visitors receive only information permitted for public display —
never IAM's private memories or another visitor's data.
"""

import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Dict, Any

from app.core.database import get_db_session, get_session_factory
from app.models.security import AuditEvent
from app.services.event_stream import fetch_audit_events, format_sse, parse_since
from app.services.source_identity import node_id_for_url
from app.models.memory import KnowledgeItem, KnowledgeSource
from app.models.publicrecords import PublicRecord
from app.models.geo import GeoPlace, LiveGeoFeed
from app.models.globalaccess import VisitorSession, VisitorLocation

router = APIRouter(prefix="/api/v1/interface", tags=["interface"])

BASE_SUGGESTIONS = {
    "focus": [
        "Research something", "Help me understand an idea", "What should I explore today?",
        "Explain a complex topic simply", "Compare two approaches", "Plan a project",
    ],
    "recall": [
        "What do you remember about me?", "Recall our previous conversation",
        "What have you learned lately?", "Summarize what we discussed",
    ],
    "create": [
        "Help me create something", "Write and test some code", "Design a small project plan",
        "Draft a document", "Brainstorm ideas with me",
    ],
}


@router.get("/suggestions")
async def get_suggestions(  # type: ignore[no-untyped-def]
    mode: str = Query("focus", pattern="^(focus|recall|create)$"),
    session_token: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """Contextual suggestions based on mode and session context."""
    suggestions = list(BASE_SUGGESTIONS.get(mode, BASE_SUGGESTIONS["focus"]))

    # If a session is provided, tailor by regional context (e.g. language) — never by private data
    if session_token:
        result = await db.execute(
            select(VisitorSession).where(VisitorSession.session_token == session_token)
        )
        session = result.scalar_one_or_none()
        if session:
            loc_result = await db.execute(
                select(VisitorLocation).where(VisitorLocation.session_id == session.id)
            )
            loc = loc_result.scalar_one_or_none()
            if loc and loc.language and loc.language.lower() != "en":
                suggestions.insert(0, f"Explain something in {loc.language}")

    return {"mode": mode, "suggestions": suggestions[:6]}


@router.get("/nodes")
async def get_public_nodes(  # type: ignore[no-untyped-def]
    limit: int = 6,
    db: AsyncSession = Depends(get_db_session),
):
    """Permission-filtered memory nodes for the orbiting sphere.

    Only verified public knowledge is shown — never private IAM memories,
    visitor conversations, or any other user's data.
    """
    result = await db.execute(
        select(KnowledgeItem)
        .where(KnowledgeItem.verification_status == "verified")
        .order_by(KnowledgeItem.created_at.desc())
        .limit(limit)
    )
    items = result.scalars().all()
    nodes = []
    for item in items:
        nodes.append({
            "text": (item.title or item.topic or "Knowledge")[:40],
            "type": "public_knowledge",
        })

    if not nodes:
        nodes = [
            {"text": "Research", "type": "capability"},
            {"text": "Memory", "type": "capability"},
            {"text": "Learning", "type": "capability"},
        ]
    return {"nodes": nodes}


PUBLIC_ACTIVITY_TYPES = {
    "research.started",
    "research.search_completed",
    "research.source_discovered",
    "research.page_opened",
    "research.source_extracted",
    "research.memory_stored",
    "research.completed",
    "knowledge.connected",
    "memory.retrieved",
}

ACTIVITY_DETAIL_KEYS = (
    "label", "activity_id", "source", "node_id",
    "from_node", "to_node", "from_cluster", "to_cluster",
    "source_count", "memory_class", "result_count", "nodes",
)


class ActivityRequest(BaseModel):
    since: Optional[str] = None


def _public_activity_payload(row) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
    details = row.details or {}
    return {
        "id": str(row.id),
        "event_type": row.event_type,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "details": {k: details[k] for k in ACTIVITY_DETAIL_KEYS if k in details},
    }


@router.get("/map")
async def public_map_data(limit: int = 60) -> Any:
    """Public geospatial markers for the single-screen map layer."""
    async with get_session_factory()() as db:
        places = (
            await db.execute(
                select(GeoPlace)
                .order_by(GeoPlace.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        feeds = (await db.execute(select(LiveGeoFeed))).scalars().all()
    return {
        "places": [
            {
                "name": p.name,
                "latitude": p.latitude,
                "longitude": p.longitude,
                "country_code": p.country_code,
                "place_type": p.place_type,
                "source": p.source,
                "confidence": p.confidence,
            }
            for p in places
        ],
        "live_feeds": len(feeds),
        "claim": "public_geospatial_context_only",
    }


@router.get("/clusters")
async def public_knowledge_clusters(limit: int = 8) -> Any:
    """Public topic clusters built only from verified knowledge records."""
    async with get_session_factory()() as db:
        result = await db.execute(
            select(KnowledgeItem.topic, func.count(KnowledgeItem.id))
            .where(
                KnowledgeItem.verification_status == "verified",
                KnowledgeItem.topic.isnot(None),
            )
            .group_by(KnowledgeItem.topic)
            .order_by(func.count(KnowledgeItem.id).desc())
            .limit(limit)
        )
    clusters = [
        {
            "name": topic[:40],
            "count": count,
            "node_id": node_id_for_url(f"cluster:{topic}"),
        }
        for topic, count in result.all()
    ]
    if not clusters:
        clusters = [
            {"name": name, "count": 0, "node_id": node_id_for_url(f"cluster:{name}")}
            for name in ("Research", "Memory", "Learning")
        ]
    return {"clusters": clusters}


@router.get("/connections")
async def public_knowledge_connections(limit: int = 20) -> Any:
    """Recent, privacy-filtered links between public knowledge nodes."""
    async with get_session_factory()() as db:
        rows = (
            await db.execute(
                select(AuditEvent)
                .where(AuditEvent.event_type == "knowledge.connected")
                .order_by(AuditEvent.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
    connections = []
    for row in rows:
        details = row.details or {}
        if not details.get("from_node") or not details.get("to_node"):
            continue
        connections.append(
            {
                "id": str(row.id),
                "from_node": details["from_node"],
                "to_node": details["to_node"],
                "from_cluster": details.get("from_cluster"),
                "to_cluster": details.get("to_cluster"),
                "relation": details.get("relation", "related"),
                "label": details.get("label"),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return {"connections": connections}


def _freshness_state(status: str, reviewed_at, created_at, accessed_at) -> tuple[str, str]:  # type: ignore[no-untyped-def]
    """Map verification and dates to a visual state. Worst state wins upstream."""
    if status in {"disputed", "retracted"}:
        return "contradicted", "Contradicted or withdrawn"
    if status == "unverified":
        return "unverified", "Not independently verified"
    now = datetime.now(timezone.utc)
    def age(value):  # type: ignore[no-untyped-def]
        if not value:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return (now - value).days

    reviewed = age(reviewed_at)  # type: ignore[no-untyped-call]
    accessed = age(accessed_at)  # type: ignore[no-untyped-call]
    created = age(created_at)  # type: ignore[no-untyped-call]
    oldest_signal = max([x for x in (reviewed, accessed, created) if x is not None], default=None)
    if oldest_signal is None:
        return "needs_review", "No verification date recorded"
    if oldest_signal > 365:
        return "historical", "Historical record"
    if oldest_signal > 180:
        return "stale", "May be outdated"
    if oldest_signal > 90:
        return "needs_review", "Periodic review due"
    return "current", "Verified and current"


@router.get("/freshness")
async def public_freshness_map(limit: int = 100) -> Any:
    """Privacy-safe freshness/verification state for sphere nodes."""
    nodes: Dict[str, Dict[str, Any]] = {}

    def merge(node_id: str, payload: Dict[str, Any]) -> None:
        rank = {"contradicted": 0, "unverified": 1, "historical": 2, "stale": 3, "needs_review": 4, "current": 5}
        old = nodes.get(node_id)
        if old and rank.get(old["state"], 9) <= rank.get(payload["state"], 9):
            return
        nodes[node_id] = payload

    async with get_session_factory()() as db:
        sources = (
            await db.execute(
                select(KnowledgeSource, KnowledgeItem)
                .join(KnowledgeItem, KnowledgeSource.knowledge_item_id == KnowledgeItem.id)
                .order_by(KnowledgeSource.access_date.desc())
                .limit(limit)
            )
        ).all()
        for source, item in sources:
            if not source.url:
                continue
            state, label = _freshness_state(
                item.verification_status,
                item.last_reviewed_at,
                item.created_at,
                source.access_date,
            )
            merge(
                node_id_for_url(source.url),
                {
                    "state": state,
                    "label": label,
                    "confidence": float(item.confidence_level or 0),
                    "last_checked_at": source.access_date.isoformat() if source.access_date else None,
                },
            )

        records = (
            await db.execute(select(PublicRecord).order_by(PublicRecord.retrieved_at.desc()).limit(limit))
        ).scalars().all()
        for record in records:
            if not record.source_url:
                continue
            state, label = _freshness_state(
                record.status if record.status in {"verified", "self_reported", "uncertain"} else "unverified",
                None,
                record.retrieved_at,
                record.retrieved_at,
            )
            merge(
                node_id_for_url(record.source_url),
                {
                    "state": state,
                    "label": label,
                    "confidence": record.confidence,
                    "last_checked_at": record.retrieved_at.isoformat() if record.retrieved_at else None,
                },
            )
    return {"nodes": nodes}


@router.get("/provenance")
async def public_cluster_provenance(cluster: str, limit: int = 8) -> Any:
    """Sources behind a verified public knowledge cluster.

    Provenance only — no private memory, conversations or unverified claims.
    """
    async with get_session_factory()() as db:
        items = (
            await db.execute(
                select(KnowledgeItem)
                .where(
                    KnowledgeItem.verification_status == "verified",
                    KnowledgeItem.topic == cluster,
                )
                .order_by(KnowledgeItem.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()

        result = []
        for item in items:
            sources = (
                await db.execute(
                    select(KnowledgeSource).where(
                        KnowledgeSource.knowledge_item_id == item.id
                    )
                )
            ).scalars().all()
            result.append(
                {
                    "title": item.title,
                    "summary": (item.content or "")[:180],
                    "confidence": float(item.confidence_level or 0),
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "sources": [
                        {
                            "title": source.title or source.url or "Source",
                            "url": source.url,
                            "domain": urlparse(source.url).netloc if source.url else "",
                            "node_id": node_id_for_url(source.url) if source.url else None,
                            "credibility": float(source.credibility_score or 0),
                        }
                        for source in sources
                    ],
                }
            )
    return {
        "cluster": cluster,
        "items": result,
        "claim": "provenance_only_not_proof",
    }


@router.post("/activity")
async def public_activity_snapshot(payload: ActivityRequest) -> Any:
    """Finite activity snapshot for polling through proxies that buffer SSE."""
    cursor = parse_since(payload.since)
    async with get_session_factory()() as db:
        rows = await fetch_audit_events(db, cursor, 100)
    return {
        "events": [
            _public_activity_payload(row)
            for row in rows
            if row.event_type in PUBLIC_ACTIVITY_TYPES
        ]
    }


@router.get("/activity")
async def public_activity_stream(  # type: ignore[no-untyped-def]
    request: Request,
    since: Optional[str] = None,
    interval: float = 1.5,
):
    """Public, privacy-filtered activity events for the living sphere.

    Only research/provenance signals are exposed. No research query text,
    actor identity, private memory or visitor data is streamed.
    """
    cursor = parse_since(since)
    poll_seconds = max(0.5, min(interval, 10.0))
    seen: set[str] = set()

    async def generate():  # type: ignore[no-untyped-def]
        nonlocal cursor
        while not await request.is_disconnected():
            async with get_session_factory()() as db:
                rows = await fetch_audit_events(db, cursor, 100)
            for row in rows:
                payload = {
                    "id": str(row.id),
                    "event_type": row.event_type,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                if payload["id"] in seen:
                    continue
                seen.add(payload["id"])  # type: ignore[arg-type]
                cursor = parse_since(payload["created_at"]) or cursor  # type: ignore[arg-type]
                if row.event_type not in PUBLIC_ACTIVITY_TYPES:
                    continue
                details: Any = row.details or {}
                public = {k: details[k] for k in ACTIVITY_DETAIL_KEYS if k in details}
                yield format_sse("activity", {**payload, "details": public})
            await asyncio.sleep(poll_seconds)

    return StreamingResponse(
        generate(),  # type: ignore[no-untyped-call]
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.post("/activity/stream")
async def public_activity_stream_post(  # type: ignore[no-untyped-def]
    payload: ActivityRequest,
    request: Request,
):
    """POST variant of the activity stream (works through dev proxy streaming)."""
    cursor = parse_since(payload.since)
    poll_seconds = 1.5
    seen: set[str] = set()

    async def generate():  # type: ignore[no-untyped-def]
        nonlocal cursor
        while not await request.is_disconnected():
            async with get_session_factory()() as db:
                rows = await fetch_audit_events(db, cursor, 100)
            for row in rows:
                event_id = str(row.id)
                item = {
                    "id": event_id,
                    "event_type": row.event_type,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                if event_id in seen:
                    continue
                seen.add(event_id)
                cursor = parse_since(item["created_at"]) or cursor  # type: ignore[arg-type]
                if row.event_type not in PUBLIC_ACTIVITY_TYPES:
                    continue
                details: Any = row.details or {}
                public = {k: details[k] for k in ACTIVITY_DETAIL_KEYS if k in details}
                yield format_sse("activity", {**item, "details": public})
            await asyncio.sleep(poll_seconds)

    return StreamingResponse(
        generate(),  # type: ignore[no-untyped-call]
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )
