"""Scheduled activities routes - background activity triggers"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db_session
from app.models.autonomy import ScheduledActivity

router = APIRouter(prefix="/api/v1/autonomy/schedule", tags=["autonomy"])


class ScheduledActivityCreate(BaseModel):
    name: str
    cron_expression: Optional[str] = None
    next_run_at: Optional[str] = None


class ScheduledActivityUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    next_run_at: Optional[str] = None
    is_active: Optional[bool] = None


class ScheduledActivityResponse(BaseModel):
    id: str
    name: str
    cron_expression: Optional[str]
    next_run_at: Optional[str]
    is_active: bool
    last_run_at: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ScheduledActivityResponse])
async def list_scheduled_activities(db: AsyncSession = Depends(get_db_session)):
    """List all scheduled activities."""
    result = await db.execute(select(ScheduledActivity).order_by(ScheduledActivity.created_at.desc()))
    activities = result.scalars().all()
    return [
        ScheduledActivityResponse(
            id=str(a.id),
            name=a.name,
            cron_expression=a.cron_expression,
            next_run_at=a.next_run_at.isoformat() if a.next_run_at else None,
            is_active=a.is_active,
            last_run_at=a.last_run_at.isoformat() if a.last_run_at else None,
            created_at=a.created_at.isoformat() if a.created_at else None,
        )
        for a in activities
    ]


@router.post("/", response_model=ScheduledActivityResponse)
async def create_scheduled_activity(
    activity: ScheduledActivityCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new scheduled background activity."""
    a = ScheduledActivity(
        name=activity.name,
        cron_expression=activity.cron_expression,
        next_run_at=datetime.fromisoformat(activity.next_run_at) if activity.next_run_at else None,
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)

    return ScheduledActivityResponse(
        id=str(a.id),
        name=a.name,
        cron_expression=a.cron_expression,
        next_run_at=a.next_run_at.isoformat() if a.next_run_at else None,
        is_active=a.is_active,
        last_run_at=a.last_run_at.isoformat() if a.last_run_at else None,
        created_at=a.created_at.isoformat() if a.created_at else None,
    )


@router.patch("/{activity_id}", response_model=ScheduledActivityResponse)
async def update_scheduled_activity(
    activity_id: str,
    update: ScheduledActivityUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update a scheduled activity."""
    result = await db.execute(select(ScheduledActivity).where(ScheduledActivity.id == activity_id))
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Scheduled activity not found")

    update_data = update.model_dump(exclude_unset=True)
    if "next_run_at" in update_data and update_data["next_run_at"] is not None:
        update_data["next_run_at"] = datetime.fromisoformat(update_data["next_run_at"])

    for key, value in update_data.items():
        if hasattr(activity, key):
            setattr(activity, key, value)

    await db.commit()
    await db.refresh(activity)

    return ScheduledActivityResponse(
        id=str(activity.id),
        name=activity.name,
        cron_expression=activity.cron_expression,
        next_run_at=activity.next_run_at.isoformat() if activity.next_run_at else None,
        is_active=activity.is_active,
        last_run_at=activity.last_run_at.isoformat() if activity.last_run_at else None,
        created_at=activity.created_at.isoformat() if activity.created_at else None,
    )
