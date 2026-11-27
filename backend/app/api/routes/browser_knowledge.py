"""Web Knowledge Integration API — governed proposals (Doc 29 P4)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.web_knowledge_integration import (
    WebKnowledgeIntegrationError,
    WebKnowledgeIntegrationService,
)

router = APIRouter(prefix="/api/v1/browser/knowledge", tags=["browser-knowledge"])


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "sdk") if credential else "sdk"


class ProposalRequest(BaseModel):
    task_id: str
    claim: str
    sources: List[Dict[str, Any]] = Field(min_length=1)
    legal_source_id: Optional[str] = None
    jurisdiction: Optional[str] = None


class RejectRequest(BaseModel):
    reason: str = ""


@router.post("/proposals", status_code=201)
async def create_proposal(
    payload: ProposalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    return await WebKnowledgeIntegrationService(db).propose(
        task_id=payload.task_id,
        claim=payload.claim,
        sources=payload.sources,
        created_by=_actor(request),
        legal_source_id=payload.legal_source_id,
        jurisdiction=payload.jurisdiction,
    )


@router.get("/proposals")
async def list_proposals(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
) -> List[Dict[str, Any]]:
    return await WebKnowledgeIntegrationService(db).list(status)


@router.get("/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await WebKnowledgeIntegrationService(db).get(proposal_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await WebKnowledgeIntegrationService(db).approve(
            proposal_id, _actor(request)
        )
    except (WebKnowledgeIntegrationError, ValueError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str,
    payload: RejectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await WebKnowledgeIntegrationService(db).reject(
            proposal_id, _actor(request), payload.reason
        )
    except (WebKnowledgeIntegrationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
