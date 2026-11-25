"""Task routes - individual activities within plans"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db_session
from app.models.autonomy import Task, TaskExecution

router = APIRouter(prefix="/api/v1/autonomy/tasks", tags=["autonomy"])


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    plan_id: Optional[str] = None
    tool_used: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    tool_used: Optional[str] = None


class TaskResponse(BaseModel):
    id: str
    plan_id: Optional[str]
    title: str
    description: Optional[str]
    status: str
    tool_used: Optional[str]
    created_at: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class TaskExecutionCreate(BaseModel):
    task_id: str
    status: str  # success, failure, partial
    output: Optional[str] = None
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


class TaskExecutionResponse(BaseModel):
    id: str
    task_id: str
    status: str
    output: Optional[str]
    error_message: Optional[str]
    duration_ms: Optional[int]
    executed_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db_session)):
    """List all tasks."""
    result = await db.execute(select(Task).order_by(Task.created_at.desc()))
    tasks = result.scalars().all()
    return [
        TaskResponse(
            id=str(t.id),
            plan_id=str(t.plan_id) if t.plan_id else None,
            title=t.title,
            description=t.description,
            status=t.status,
            tool_used=t.tool_used,
            created_at=t.created_at.isoformat() if t.created_at else None,
            started_at=t.started_at.isoformat() if t.started_at else None,
            completed_at=t.completed_at.isoformat() if t.completed_at else None,
        )
        for t in tasks
    ]


@router.post("/", response_model=TaskResponse)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db_session)):
    """Create a new task."""
    t = Task(
        title=task.title,
        description=task.description,
        plan_id=task.plan_id,
        tool_used=task.tool_used,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)

    return TaskResponse(
        id=str(t.id),
        plan_id=str(t.plan_id) if t.plan_id else None,
        title=t.title,
        description=t.description,
        status=t.status,
        tool_used=t.tool_used,
        created_at=t.created_at.isoformat() if t.created_at else None,
        started_at=t.started_at.isoformat() if t.started_at else None,
        completed_at=t.completed_at.isoformat() if t.completed_at else None,
    )


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, update: TaskUpdate, db: AsyncSession = Depends(get_db_session)):
    """Update task status or details."""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = update.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"] is not None:
        if update_data["status"] == "in_progress" and not task.started_at:
            update_data["started_at"] = datetime.utcnow()
        if update_data["status"] in ("completed", "failed") and not task.completed_at:
            update_data["completed_at"] = datetime.utcnow()

    for key, value in update_data.items():
        if hasattr(task, key):
            setattr(task, key, value)

    await db.commit()
    await db.refresh(task)

    return TaskResponse(
        id=str(task.id),
        plan_id=str(task.plan_id) if task.plan_id else None,
        title=task.title,
        description=task.description,
        status=task.status,
        tool_used=task.tool_used,
        created_at=task.created_at.isoformat() if task.created_at else None,
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
    )


@router.post("/executions", response_model=TaskExecutionResponse)
async def record_task_execution(
    execution: TaskExecutionCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Record a task execution result."""
    # Verify task exists
    result = await db.execute(select(Task).where(Task.id == execution.task_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Task not found")

    te = TaskExecution(
        task_id=execution.task_id,
        status=execution.status,
        output=execution.output,
        error_message=execution.error_message,
        duration_ms=execution.duration_ms,
    )
    db.add(te)
    await db.commit()
    await db.refresh(te)

    return TaskExecutionResponse(
        id=str(te.id),
        task_id=str(te.task_id),
        status=te.status,
        output=te.output,
        error_message=te.error_message,
        duration_ms=te.duration_ms,
        executed_at=te.executed_at.isoformat() if te.executed_at else None,
    )


@router.get("/{task_id}/executions", response_model=List[TaskExecutionResponse])
async def list_task_executions(task_id: str, db: AsyncSession = Depends(get_db_session)):
    """List all executions for a task."""
    result = await db.execute(
        select(TaskExecution)
        .where(TaskExecution.task_id == task_id)
        .order_by(TaskExecution.executed_at.desc())
    )
    executions = result.scalars().all()
    return [
        TaskExecutionResponse(
            id=str(e.id),
            task_id=str(e.task_id),
            status=e.status,
            output=e.output,
            error_message=e.error_message,
            duration_ms=e.duration_ms,
            executed_at=e.executed_at.isoformat() if e.executed_at else None,
        )
        for e in executions
    ]
