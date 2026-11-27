"""Research routes - web research, source verification, knowledge evaluation"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.core.database import get_db_session
from app.services.model_policy import (
    ModelPolicyDenied,
    SEARCH_ACTION,
    require_authorization,
)
from app.services.research_service import research_service
from app.services.browser_service import browser_service
from app.services.search_service import search_service

router = APIRouter(prefix="/api/v1/research", tags=["research"])


class ResearchRequest(BaseModel):
    query: str
    store_as_memory: bool = True
    store_as_knowledge: bool = False
    max_results: int = 10


class ResearchResponse(BaseModel):
    query: str
    started_at: Optional[str]
    completed_at: Optional[str]
    sources: List[Dict[str, Any]]
    findings: List[Dict[str, Any]]
    credibility_score: float
    source_count: int


class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    provider: Optional[str] = None


class BrowseRequest(BaseModel):
    url: str
    extract_text: bool = True
    extract_links: bool = False
    extract_metadata: bool = True


class VerifyRequest(BaseModel):
    knowledge_id: str


@router.post("/", response_model=ResearchResponse)
async def research_topic(request: ResearchRequest):
    """
    Run a full research workflow: search → browse → extract → store.
    
    Results are stored in memory with provenance tracking. High-credibility
    results can optionally be stored as knowledge items.
    """
    result = await research_service.research_topic(
        query=request.query,
        store_as_memory=request.store_as_memory,
        store_as_knowledge=request.store_as_knowledge,
        max_results=request.max_results,
    )
    return result


@router.post("/search")
async def search_web(request: SearchRequest, db: Any = Depends(get_db_session)) -> Any:
    """Search the web using configured provider.

    Paid providers (Brave/Google) require a signed Creator authorization; the
    Wikipedia fallback is free and needs none.
    """
    if request.provider in {"brave", "google"}:
        try:
            await require_authorization(
                db, SEARCH_ACTION, target_ref=request.provider
            )
        except ModelPolicyDenied as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    result = await search_service.search(
        query=request.query,
        max_results=request.max_results,
        provider=request.provider,
    )
    return result


@router.post("/browse")
async def browse_page(request: BrowseRequest):
    """Fetch and extract content from a single web page."""
    result = await browser_service.fetch_page(
        url=request.url,
        extract_text=request.extract_text,
        extract_links=request.extract_links,
        extract_metadata=request.extract_metadata,
    )
    return result


@router.post("/search-browse")
async def search_and_browse(request: SearchRequest):
    """Search via DuckDuckGo browser, then browse top results."""
    results = await browser_service.search_duckduckgo(
        query=request.query, max_results=request.max_results
    )
    browsed = []
    for r in results[:5]:
        page_data = await browser_service.fetch_page(
            url=r.get("url", ""),
            extract_text=True,
            extract_metadata=True,
        )
        browsed.append({
            "search_result": r,
            "page": page_data,
        })
    return {
        "query": request.query,
        "results": browsed,
        "count": len(browsed),
    }


@router.post("/verify")
async def verify_knowledge(request: VerifyRequest):
    """Cross-reference a knowledge item against multiple sources."""
    result = await research_service.verify_knowledge_against_sources(
        knowledge_id=request.knowledge_id
    )
    return result
