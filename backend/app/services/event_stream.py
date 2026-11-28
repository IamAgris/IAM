"""Helpers for the version-neutral ``/events`` server-sent event stream.

The durable source of events is ``audit_events``. Using the audit trail instead
of an in-memory bus means a backend restart does not lose events, and every
streamed event keeps the same actor/target/provenance fields as the audit log.
"""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import AuditEvent


def parse_since(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 cursor, returning an aware UTC datetime."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        # A malformed cursor must fail soft: the public activity poll sends a
        # fresh cursor every 2s and a single bad value must not return HTTP 500.
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def audit_event_payload(row: AuditEvent) -> Dict[str, Any]:
    """Convert an audit row into a language-neutral event payload."""
    return {
        "id": str(row.id),
        "event_type": row.event_type,
        "actor": row.actor,
        "target": row.target,
        "details": row.details or {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def format_sse(event: str, data: Dict[str, Any]) -> str:
    """Render one SSE frame (single-line JSON, safe for EventSource clients)."""
    return f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


async def fetch_audit_events(
    db: AsyncSession, since: Optional[datetime], limit: int
) -> list[AuditEvent]:
    """Return audit events newer than ``since`` in chronological order."""
    query = select(AuditEvent)
    if since is not None:
        query = query.where(AuditEvent.created_at > since)
    query = query.order_by(AuditEvent.created_at.asc(), AuditEvent.id.asc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
