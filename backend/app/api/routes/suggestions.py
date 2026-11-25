"""Contextual suggestions and public memory nodes for the IAM interface.

Public visitors receive only information permitted for public display —
never IAM's private memories or another visitor's data.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any

from app.core.database import get_db_session
from app.models.memory import KnowledgeItem
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
async def get_suggestions(
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
async def get_public_nodes(
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
