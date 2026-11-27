"""Privacy-safe public activity signals for live web evidence.

The orbiting sphere reads only the public AuditEvent stream. Live chat search
must not write visitor queries, pasted links or private memory there, so this
module emits fingerprint-only source signals: a deterministic node id, the
public domain and an empty URL. No query text or raw URL ever enters an event.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable
from urllib.parse import urlparse
from uuid import uuid4

from sqlalchemy import select

from app.models.security import AuditEvent
from app.services.source_identity import node_id_for_url

_MAX_PUBLIC_SOURCES = 3


async def emit_public_search_activity(db: Any, results: Iterable[Dict[str, Any]]) -> bool:
    """Publish fingerprint-only source dots for fresh live-search results.

    Returns True when at least one new source was published. Duplicate sources
    are skipped so repeated chats do not fill the sphere with the same nodes.
    """
    visible: list[tuple[str, str]] = []
    for item in results or []:
        url = str(item.get("url") or "") if isinstance(item, dict) else ""
        if not url.startswith(("http://", "https://")):
            continue
        domain = urlparse(url).netloc
        if not domain:
            continue
        visible.append((node_id_for_url(url), domain))
        if len(visible) >= _MAX_PUBLIC_SOURCES:
            break
    if not visible:
        return False

    activity_id = uuid4().hex
    db.add(
        AuditEvent(
            event_type="research.search_completed",
            actor="live-search",
            target="public-web",
            details={
                "activity_id": activity_id,
                "label": "Searching web",
                "result_count": len(visible),
            },
        )
    )

    published = False
    for node_id, domain in visible:
        existing = await db.execute(
            select(AuditEvent.id)
            .where(
                AuditEvent.event_type == "research.source_discovered",
                AuditEvent.target == node_id,
            )
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            continue
        db.add(
            AuditEvent(
                event_type="research.source_discovered",
                actor="live-search",
                target=node_id,
                details={
                    "activity_id": activity_id,
                    "label": "Discovering sources",
                    "source": {
                        "node_id": node_id,
                        "title": domain,
                        "domain": domain,
                        "url": "",  # never expose a raw or visitor-pasted URL
                    },
                },
            )
        )
        published = True
    await db.commit()
    return published
