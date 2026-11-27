"""Shared Web Intelligence Engine API (proposed Doc 32).

Gives authorised agents, specialist intelligences and background research the
same live-information capability the main chat uses. No separate search stack:
this delegates to the shared policy, cache and existing search/browser services.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.live_information_policy import (
    WEB_ACCESS_POLICY,
    SearchTriggerClassifier,
    collect_live_evidence,
)

router = APIRouter(prefix="/api/v1/live-information", tags=["live-information"])


class LiveResearchRequest(BaseModel):
    query: str
    max_results: int = Field(default=3, ge=1, le=10)


@router.get("/policy")
async def live_information_policy() -> Dict[str, Any]:
    """The standing rule injected into every IAM chat request."""
    return {"policy": WEB_ACCESS_POLICY}


@router.post("/research")
async def live_research(
    request: LiveResearchRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Classify intent and retrieve live evidence through the shared engine."""
    trigger = SearchTriggerClassifier().classify(request.query)
    if not trigger.needs_search:
        return {
            "query": request.query,
            "needs_search": False,
            "reason": trigger.reason,
            "results": [],
            "errors": [],
        }
    evidence = await collect_live_evidence(
        request.query, trigger=trigger, max_results=request.max_results, db=db
    )
    return {
        "query": request.query,
        "needs_search": True,
        "categories": list(trigger.categories),
        "preferred_sources": list(trigger.preferred_sources),
        "depth": trigger.depth.value,
        "provider": evidence.provider,
        "retrieved_at": evidence.retrieved_at,
        "results": evidence.results,
        "errors": evidence.errors,
        "system_message": evidence.as_system_message(),
    }
