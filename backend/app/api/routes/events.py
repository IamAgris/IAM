"""Server-sent event stream backed by the durable audit trail."""

import asyncio
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.database import get_session_factory
from app.services.event_stream import (
    audit_event_payload,
    fetch_audit_events,
    format_sse,
    parse_since,
)

router = APIRouter(prefix="/api/v1", tags=["events"])


@router.get("/events")
async def event_stream(
    request: Request,
    since: Optional[str] = None,
    limit: int = 100,
    interval: float = 2.0,
):
    """Stream audit events as SSE.

    Clients reconnect with the ``created_at`` of the last event they saw as
    ``?since=``. Events are durable (stored in ``audit_events``), so reconnect
    replays anything missed while disconnected.
    """
    cursor = parse_since(since)
    bounded_limit = max(1, min(limit, 500))
    poll_seconds = max(0.5, min(interval, 30.0))
    seen: set[str] = set()

    async def generate():
        nonlocal cursor
        while not await request.is_disconnected():
            async with get_session_factory()() as db:
                rows = await fetch_audit_events(db, cursor, bounded_limit)
            fresh = []
            for row in rows:
                payload = audit_event_payload(row)
                if payload["id"] in seen:
                    continue
                seen.add(payload["id"])
                fresh.append(payload)
            if fresh:
                for payload in fresh:
                    cursor = parse_since(payload["created_at"]) or cursor
                    yield format_sse("audit", payload)
                continue
            yield ": keep-alive\n\n"
            await asyncio.sleep(poll_seconds)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
