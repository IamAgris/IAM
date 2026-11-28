"""Multi-agent browser session API (Doc 29 P7)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.browser_multi_agent import (
    BrowserMultiAgentError,
    BrowserMultiAgentService,
)

router = APIRouter(prefix="/api/v1/browser/agents", tags=["browser-agents"])


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "sdk") if credential else "sdk"


class OpenSessionRequest(BaseModel):
    agent_id: str
    mode: str = "isolated"
    permission_scope: List[str] = Field(default_factory=list)
    task_id: Optional[str] = None


class CloseSessionRequest(BaseModel):
    agent_id: str


class TransferRequest(BaseModel):
    from_agent: str
    to_agent: str
    authorization_id: str


class TakeoverRequest(BaseModel):
    reason: str


class ShareWorkflowRequest(BaseModel):
    from_agent: str
    to_agent: str


@router.get("/capacity")
async def capacity(
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    return await BrowserMultiAgentService(db).capacity()


@router.post("/sessions")
async def open_session(
    payload: OpenSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserMultiAgentService(db).open_for_agent(
            payload.agent_id,
            mode=payload.mode,
            permission_scope=payload.permission_scope,
            task_id=payload.task_id,
            actor=_actor(request),
        )
    except BrowserMultiAgentError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.delete("/sessions/{session_token}")
async def close_session(
    session_token: str,
    payload: CloseSessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserMultiAgentService(db).close_for_agent(
            session_token, payload.agent_id, actor=_actor(request)
        )
    except BrowserMultiAgentError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/sessions/{session_token}/transfer")
async def transfer_session(
    session_token: str,
    payload: TransferRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserMultiAgentService(db).transfer(
            session_token,
            from_agent=payload.from_agent,
            to_agent=payload.to_agent,
            authorization_id=payload.authorization_id,
            actor=_actor(request),
        )
    except BrowserMultiAgentError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/sessions/{session_token}/takeover")
async def request_takeover(
    session_token: str,
    payload: TakeoverRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserMultiAgentService(db).request_takeover(
            session_token, reason=payload.reason, actor=_actor(request)
        )
    except BrowserMultiAgentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_token}/recover")
async def recover_session(
    session_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserMultiAgentService(db).recover(
            session_token, actor=_actor(request)
        )
    except BrowserMultiAgentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/workflows/{workflow_id}/share")
async def share_workflow(
    workflow_id: str,
    payload: ShareWorkflowRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserMultiAgentService(db).share_approved_workflow(
            workflow_id,
            from_agent=payload.from_agent,
            to_agent=payload.to_agent,
            actor=_actor(request),
        )
    except BrowserMultiAgentError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
