"""Shared Web Intelligence Engine API (proposed Doc 34).

Gives authorised agents, specialist intelligences and background research the
same live-information capability the main chat uses. No separate search stack:
this delegates to the shared policy, cache and existing search/browser services.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.services.live_information_policy import (
    WEB_ACCESS_POLICY,
    SearchTriggerClassifier,
    collect_live_evidence,
)
from app.services.live_research_monitor import LiveResearchMonitor
from app.services.search_provider_registry import search_provider_registry

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


@router.get("/providers")
async def search_providers() -> Dict[str, Any]:
    """Health, quota and cost metadata for the search provider chain."""
    return {
        "chain": search_provider_registry.chain(free_only=True),
        "parallel": settings.iam_search_concurrent_providers,
        "providers": search_provider_registry.status(),
    }


class MonitorRequest(BaseModel):
    topic: str
    query: str
    interval_minutes: int = Field(default=60, ge=15, le=10080)


@router.post("/monitor")
async def create_monitor(
    request: MonitorRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    try:
        return await LiveResearchMonitor(db).create(
            request.topic, request.query, request.interval_minutes
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/monitor")
async def list_monitors(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    return {"tasks": await LiveResearchMonitor(db).list()}


@router.delete("/monitor/{task_id}")
async def remove_monitor(
    task_id: str, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    removed = await LiveResearchMonitor(db).remove(task_id)
    if not removed:
        raise HTTPException(status_code=404, detail="task not found")
    return {"removed": True}


@router.post("/monitor/run-due")
async def run_due_monitors(
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Bounded execution of due monitoring tasks through the shared engine."""
    return {"runs": await LiveResearchMonitor(db).run_due()}
