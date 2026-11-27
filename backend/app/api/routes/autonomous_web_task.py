"""Autonomous Web Task API routes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.autonomous_web_task_service import (
    AutonomousWebTaskError,
    AutonomousWebTaskService,
)

router = APIRouter(prefix="/api/v1/web/tasks", tags=["web-tasks"])


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    website_knowledge_id: Optional[str] = None
    task_type: str
    priority: int = Field(default=5, ge=1, le=10)
    decomposition: List[Dict[str, Any]] = Field(default_factory=list)
    checkpoints: List[Dict[str, Any]] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    max_retries: int = Field(default=3, ge=0, le=10)
    is_background: bool = False


class TaskProgressUpdate(BaseModel):
    progress_percentage: int = Field(ge=0, le=100)
    status: Optional[str] = None
    error_message: Optional[str] = None
    checkpoint: Optional[Dict[str, Any]] = None


class TaskRetry(BaseModel):
    pass


class TaskCancel(BaseModel):
    pass


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _fail(exc: AutonomousWebTaskError) -> HTTPException:
    return HTTPException(400, str(exc))


@router.post("")
async def create_task(
    payload: TaskCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new autonomous web task."""
    try:
        return await AutonomousWebTaskService(db).create(
            title=payload.title,
            description=payload.description,
            website_knowledge_id=payload.website_knowledge_id,
            task_type=payload.task_type,
            priority=payload.priority,
            decomposition=payload.decomposition,
            checkpoints=payload.checkpoints,
            dependencies=payload.dependencies,
            max_retries=payload.max_retries,
            is_background=payload.is_background,
            actor=_actor(request),
        )
    except AutonomousWebTaskError as exc:
        raise _fail(exc) from exc


@router.get("")
async def list_tasks(
    website_knowledge_id: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List autonomous web tasks."""
    return await AutonomousWebTaskService(db).list(
        website_knowledge_id=website_knowledge_id, status=status
    )


@router.get("/{task_id}")
async def get_task(task_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get a single autonomous web task by ID."""
    try:
        return await AutonomousWebTaskService(db).get(task_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.patch("/{task_id}/progress")
async def update_progress(
    task_id: str,
    payload: TaskProgressUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Update task progress."""
    try:
        return await AutonomousWebTaskService(db).update_progress(
            task_id,
            progress_percentage=payload.progress_percentage,
            status=payload.status,
            error_message=payload.error_message,
            checkpoint=payload.checkpoint,
            actor=_actor(request),
        )
    except AutonomousWebTaskError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Retry a failed task."""
    try:
        return await AutonomousWebTaskService(db).retry(
            task_id, actor=_actor(request)
        )
    except AutonomousWebTaskError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Cancel a pending or executing task."""
    try:
        return await AutonomousWebTaskService(db).cancel(
            task_id, actor=_actor(request)
        )
    except AutonomousWebTaskError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc