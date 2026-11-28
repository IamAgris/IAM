"""UWAIE browser task API — Doc 29 §7.1 standard envelope."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.services.browser_engine_adapters import BrowserEngineUnavailable
from app.services.browser_evidence_service import (
    BrowserEvidenceError,
    BrowserEvidenceService,
)
from app.services.browser_service import browser_service
from app.services.internetaccess_service import InternetAccessService
from app.services.uwaie_service import UWAIEError, UWAIEService

router = APIRouter(prefix="/api/v1/browser", tags=["uwai-browser"])


class TaskRequest(BaseModel):
    task_id: Optional[str] = None
    steps: List[Dict[str, Any]] = Field(min_length=1)
    verification: Dict[str, Any] = Field(default_factory=dict)
    session_token: str
    actor: str = "sdk"
    actor_type: str = "agent"
    permission_scope: Optional[str] = None
    mode: str = "headless"
    priority: int = 5
    deadline_seconds: Optional[int] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "sdk") if credential else "sdk"


def _actor_type(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    if credential and str(credential.get("actor_type", "")) == "creator":
        return "creator"
    return "agent"


async def _ensure_run(evidence: BrowserEvidenceService, task_id: str, **kwargs: Any) -> None:
    """Create an attributed run only when the task_id is not already known."""
    try:
        await evidence.envelope(task_id)
    except BrowserEvidenceError:
        await evidence.start_run(task_id=task_id, **kwargs)


@router.post("/tasks", status_code=202)
async def create_task(
    payload: TaskRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Any:
    task_id = payload.task_id or f"browser-{uuid4().hex}"
    evidence = BrowserEvidenceService(db)
    deadline = None
    if payload.deadline_seconds:
        deadline = datetime.now(timezone.utc) + timedelta(seconds=payload.deadline_seconds)
    try:
        run = await evidence.start_run(
            task_id=task_id,
            actor=payload.actor,
            actor_type=payload.actor_type,
            permission_scope=payload.permission_scope,
            session_id=payload.session_token,
            mode=payload.mode,
            engine=settings.uwai_browser_engine,
            priority=payload.priority,
            deadline=deadline,
        )
        if settings.browser_task_worker_backend.lower() == "arq":
            from arq import create_pool
            from arq.connections import RedisSettings

            pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
            try:
                await pool.enqueue_job(
                    "run_browser_task",
                    job_id=task_id,  # idempotency: one job per browser task ID
                    task_id=task_id,
                    steps=payload.steps,
                    verification=payload.verification,
                    session_token=payload.session_token,
                    actor=payload.actor,
                    actor_type=payload.actor_type,
                    permission_scope=payload.permission_scope,
                )
            finally:
                await pool.close()
            envelope = await evidence.envelope(task_id)
            result = dict(envelope)
            result["queued"] = True
            result["run"] = run
            return result

        result = await UWAIEService(db).execute(
            steps=payload.steps,
            verification=payload.verification,
            session_token=payload.session_token,
            actor=payload.actor,
            task_id=task_id,
            actor_type=payload.actor_type,
            permission_scope=payload.permission_scope,
        )
        return result.get("envelope") or await evidence.envelope(task_id)
    except (BrowserEvidenceError, UWAIEError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    try:
        return await BrowserEvidenceService(db).envelope(task_id)
    except BrowserEvidenceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/evidence")
async def get_evidence(
    task_id: str, db: AsyncSession = Depends(get_db_session)
) -> List[Dict[str, Any]]:
    return await BrowserEvidenceService(db).evidence_for(task_id)


class SessionRequest(BaseModel):
    purpose: str = "uwaie-workflow"
    mode: str = "headless"
    permission_scope: List[str] = Field(default_factory=list)


class InspectRequest(BaseModel):
    url: str
    session_token: Optional[str] = None
    task_id: Optional[str] = None
    actor: Optional[str] = None
    actor_type: str = "agent"
    permission_scope: Optional[str] = None


class ExecuteRequest(BaseModel):
    steps: List[Dict[str, Any]] = Field(min_length=1)
    verification: Dict[str, Any] = Field(default_factory=dict)
    session_token: str
    task_id: Optional[str] = None
    actor: Optional[str] = None
    actor_type: str = "agent"
    permission_scope: Optional[str] = None
    recover: bool = True
    learn: bool = False


class VerifyRequest(BaseModel):
    session_token: str
    verification: Dict[str, Any] = Field(default_factory=dict)
    task_id: Optional[str] = None
    actor: Optional[str] = None
    actor_type: str = "agent"


@router.post("/sessions")
async def open_session(
    payload: SessionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Open a headless/visible/isolated browser session with an owner and scope."""
    created = await UWAIEService(db).create_session(payload.purpose)
    token = str(created.get("session_token") or "") if isinstance(created, dict) else ""
    if not token:
        raise HTTPException(status_code=500, detail="browsing session was not created")
    try:
        meta = await browser_service.open_session(
            token,
            mode=payload.mode,
            owner=_actor_type(request),
            permission_scope=payload.permission_scope,
        )
    except (BrowserEngineUnavailable, ValueError) as exc:
        await InternetAccessService(db).close_session(token)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**created, **meta, "status": "open"}


@router.delete("/sessions/{session_token}")
async def close_session(
    session_token: str,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    browser_closed = await browser_service.close_session(session_token)
    db_closed = await InternetAccessService(db).close_session(session_token)
    return {
        "session_id": session_token,
        "status": "closed",
        "browser_closed": browser_closed,
        "session_closed": db_closed,
    }


@router.post("/inspect")
async def inspect(
    payload: InspectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    actor = payload.actor or _actor(request)
    evidence = BrowserEvidenceService(db)
    if payload.task_id:
        await _ensure_run(
            evidence,
            payload.task_id,
            actor=actor,
            actor_type=payload.actor_type,
            permission_scope=payload.permission_scope,
            session_id=payload.session_token,
        )
    try:
        result = await UWAIEService(db).inspect(payload.url, actor)
    except UWAIEError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload.task_id:
        await evidence.append_audit(
            payload.task_id, actor=actor, actor_type=payload.actor_type,
            action="browser.inspect", target=payload.url,
            outcome={"untrusted": True},
        )
        result["envelope"] = await evidence.envelope(
            payload.task_id, session_id=payload.session_token
        )
    return result


@router.post("/execute")
async def execute(
    payload: ExecuteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    actor = payload.actor or _actor(request)
    try:
        result = await UWAIEService(db).execute(
            steps=payload.steps,
            verification=payload.verification,
            session_token=payload.session_token,
            learn=payload.learn,
            actor=actor,
            recover=payload.recover,
            task_id=payload.task_id,
            actor_type=payload.actor_type,
            permission_scope=payload.permission_scope,
        )
    except UWAIEError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/verify")
async def verify(
    payload: VerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    actor = payload.actor or _actor(request)
    result = await UWAIEService(db).verify(
        payload.verification,
        payload.session_token,
        task_id=payload.task_id,
        actor=actor,
        actor_type=payload.actor_type,
    )
    return result


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    evidence = BrowserEvidenceService(db)
    actor = _actor(request)
    try:
        run = await evidence.set_state(task_id, "cancelled")
        await evidence.append_audit(
            task_id, actor=actor, actor_type=_actor_type(request),
            action="browser.task.cancel", target=task_id,
            outcome={"status": "cancelled"},
        )
    except BrowserEvidenceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if run.get("session_id"):
        await browser_service.close_session(str(run["session_id"]))
    return await evidence.envelope(task_id, status="cancelled")
