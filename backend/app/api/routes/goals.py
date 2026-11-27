"""Autonomy routes - goals and plans"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db_session
from app.models.autonomy import Goal, Plan

router = APIRouter(prefix="/api/v1/autonomy/goals", tags=["autonomy"])


class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    priority: int = 5
    target_completion_date: Optional[str] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    target_completion_date: Optional[str] = None


class GoalResponse(BaseModel):
    id: str
    title: str
    description: Optional[str]
    status: str
    priority: int
    created_at: Optional[str]
    target_completion_date: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class PlanCreate(BaseModel):
    goal_id: str
    title: str
    steps: List[Dict[str, Any]] = []


class PlanResponse(BaseModel):
    id: str
    goal_id: str
    title: str
    steps: List[Dict[str, Any]]
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]

    class Config:
        from_attributes = True


def _clamp_priority(value: int) -> int:
    return max(1, min(10, value))


@router.get("/", response_model=List[GoalResponse])
async def list_goals(db: AsyncSession = Depends(get_db_session)):
    """List all goals."""
    result = await db.execute(select(Goal).order_by(Goal.created_at.desc()))
    goals = result.scalars().all()
    return [
        GoalResponse(
            id=str(g.id),
            title=g.title,
            description=g.description,
            status=g.status,
            priority=g.priority,
            created_at=g.created_at.isoformat() if g.created_at else None,
            target_completion_date=g.target_completion_date.isoformat() if g.target_completion_date else None,
            completed_at=g.completed_at.isoformat() if g.completed_at else None,
        )
        for g in goals
    ]


@router.post("/", response_model=GoalResponse)
async def create_goal(goal: GoalCreate, db: AsyncSession = Depends(get_db_session)):
    """Create a new independently established goal."""
    g = Goal(
        title=goal.title,
        description=goal.description,
        priority=_clamp_priority(goal.priority),
        target_completion_date=datetime.fromisoformat(goal.target_completion_date) if goal.target_completion_date else None,
    )
    db.add(g)
    await db.commit()
    await db.refresh(g)

    return GoalResponse(
        id=str(g.id),
        title=g.title,
        description=g.description,
        status=g.status,
        priority=g.priority,
        created_at=g.created_at.isoformat() if g.created_at else None,
        target_completion_date=g.target_completion_date.isoformat() if g.target_completion_date else None,
        completed_at=g.completed_at.isoformat() if g.completed_at else None,
    )


@router.patch("/{goal_id}", response_model=GoalResponse)
async def update_goal(goal_id: str, update: GoalUpdate, db: AsyncSession = Depends(get_db_session)):
    """Update goal status or details."""
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    update_data = update.model_dump(exclude_unset=True)
    if "priority" in update_data and update_data["priority"] is not None:
        update_data["priority"] = _clamp_priority(update_data["priority"])
    if "target_completion_date" in update_data and update_data["target_completion_date"] is not None:
        update_data["target_completion_date"] = datetime.fromisoformat(update_data["target_completion_date"])
    if "status" in update_data and update_data["status"] is not None:
        if update_data["status"] == "completed":
            update_data["completed_at"] = datetime.utcnow()

    for key, value in update_data.items():
        if hasattr(goal, key):
            setattr(goal, key, value)

    await db.commit()
    await db.refresh(goal)

    return GoalResponse(
        id=str(goal.id),
        title=goal.title,
        description=goal.description,
        status=goal.status,
        priority=goal.priority,
        created_at=goal.created_at.isoformat() if goal.created_at else None,
        target_completion_date=goal.target_completion_date.isoformat() if goal.target_completion_date else None,
        completed_at=goal.completed_at.isoformat() if goal.completed_at else None,
    )


@router.post("/plans", response_model=PlanResponse)
async def create_plan(plan: PlanCreate, db: AsyncSession = Depends(get_db_session)):
    """Create a plan associated with a goal."""
    # Verify goal exists
    result = await db.execute(select(Goal).where(Goal.id == plan.goal_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Goal not found")

    p = Plan(
        goal_id=plan.goal_id,
        title=plan.title,
        steps=plan.steps,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)

    return PlanResponse(
        id=str(p.id),
        goal_id=str(p.goal_id),
        title=p.title,
        steps=p.steps,
        status=p.status,
        created_at=p.created_at.isoformat() if p.created_at else None,
        updated_at=p.updated_at.isoformat() if p.updated_at else None,
    )


@router.get("/{goal_id}/plans", response_model=List[PlanResponse])
async def list_plans(goal_id: str, db: AsyncSession = Depends(get_db_session)):
    """List all plans for a goal."""
    result = await db.execute(select(Plan).where(Plan.goal_id == goal_id))
    plans = result.scalars().all()
    return [
        PlanResponse(
            id=str(p.id),
            goal_id=str(p.goal_id),
            title=p.title,
            steps=p.steps,
            status=p.status,
            created_at=p.created_at.isoformat() if p.created_at else None,
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )
        for p in plans
    ]
