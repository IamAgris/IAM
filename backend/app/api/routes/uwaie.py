"""Universal Website and Application Interaction routes (OD-27).

Frontend-first, permission-gated, verified website interaction. No credentials,
cookies or sessions are stored in workflow knowledge.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.uwaie_service import UWAIEError, UWAIEService

router = APIRouter(prefix="/api/v1/uwaie", tags=["uwaie"])


class InspectRequest(BaseModel):
    url: str


class SessionRequest(BaseModel):
    purpose: str = "uwaie-workflow"


class ApproveWorkflowRequest(BaseModel):
    approval_id: str


class ReuseWorkflowRequest(BaseModel):
    url: str
    session_token: Optional[str] = None


class HandoverRequest(BaseModel):
    url: str
    reason: str


class ExecuteRequest(BaseModel):
    steps: List[Dict[str, Any]]
    verification: Dict[str, Any]
    session_token: Optional[str] = None
    learn: bool = False
    workflow_name: Optional[str] = None
    recover: bool = True


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


@router.post("/sessions")
async def create_session(payload: SessionRequest, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Create an isolated browser session for a website workflow."""
    return await UWAIEService(db).create_session(payload.purpose)


@router.post("/inspect")
async def inspect(  # type: ignore[no-untyped-def]
    payload: InspectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await UWAIEService(db).inspect(payload.url, _actor(request))
    except UWAIEError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/execute")
async def execute(  # type: ignore[no-untyped-def]
    payload: ExecuteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await UWAIEService(db).execute(
            steps=payload.steps,
            verification=payload.verification,
            session_token=payload.session_token,
            learn=payload.learn,
            workflow_name=payload.workflow_name,
            actor=_actor(request),
            recover=payload.recover,
        )
    except UWAIEError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/workflows")
async def workflows(  # type: ignore[no-untyped-def]
    approved_only: bool = False,
    db: AsyncSession = Depends(get_db_session),
):
    return await UWAIEService(db).list_workflows(approved_only)


@router.post("/workflows/{workflow_id}/approve")
async def approve_workflow(  # type: ignore[no-untyped-def]
    workflow_id: str,
    payload: ApproveWorkflowRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await UWAIEService(db).approve_workflow(
            workflow_id, payload.approval_id, _actor(request)
        )
    except UWAIEError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/workflows/{workflow_id}/reuse")
async def reuse_workflow(  # type: ignore[no-untyped-def]
    workflow_id: str,
    payload: ReuseWorkflowRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await UWAIEService(db).reuse_workflow(
            workflow_id, payload.url, payload.session_token, _actor(request)
        )
    except UWAIEError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/handover")
async def request_handover(  # type: ignore[no-untyped-def]
    payload: HandoverRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await UWAIEService(db).request_handover(
            payload.url, payload.reason, _actor(request)
        )
    except UWAIEError as exc:
        raise HTTPException(400, str(exc)) from exc
