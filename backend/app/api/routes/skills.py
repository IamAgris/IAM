"""Skills routes - acquired skills and procedures"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db_session
from app.models.memory import Skill

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


class SkillCreate(BaseModel):
    name: str
    category: Optional[str] = None
    proficiency_level: int = 0
    description: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SkillUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    proficiency_level: Optional[int] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SkillResponse(BaseModel):
    id: str
    name: str
    category: Optional[str]
    proficiency_level: int
    description: Optional[str]
    acquired_at: Optional[str]
    last_practiced_at: Optional[str]
    metadata: Dict[str, Any]

    class Config:
        from_attributes = True


def _clamp(value: int) -> int:
    return max(0, min(100, value))


@router.get("/", response_model=List[SkillResponse])
async def list_skills(db: AsyncSession = Depends(get_db_session)):
    """List all acquired skills."""
    result = await db.execute(select(Skill).order_by(Skill.acquired_at.desc()))
    skills = result.scalars().all()
    return [
        SkillResponse(
            id=str(s.id),
            name=s.name,
            category=s.category,
            proficiency_level=s.proficiency_level,
            description=s.description,
            acquired_at=s.acquired_at.isoformat() if s.acquired_at else None,
            last_practiced_at=s.last_practiced_at.isoformat() if s.last_practiced_at else None,
            metadata=s.metadata_ or {},
        )
        for s in skills
    ]


@router.post("/", response_model=SkillResponse)
async def create_skill(skill: SkillCreate, db: AsyncSession = Depends(get_db_session)):
    """Record a newly acquired skill."""
    s = Skill(
        name=skill.name,
        category=skill.category,
        proficiency_level=_clamp(skill.proficiency_level),
        description=skill.description,
        metadata_=skill.metadata,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)

    return SkillResponse(
        id=str(s.id),
        name=s.name,
        category=s.category,
        proficiency_level=s.proficiency_level,
        description=s.description,
        acquired_at=s.acquired_at.isoformat() if s.acquired_at else None,
        last_practiced_at=s.last_practiced_at.isoformat() if s.last_practiced_at else None,
        metadata=s.metadata_ or {},
    )


@router.patch("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    update: SkillUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update skill proficiency or details."""
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    skill = result.scalar_one_or_none()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(skill, key):
            if key == "proficiency_level" and value is not None:
                setattr(skill, key, _clamp(value))
            else:
                setattr(skill, key, value)

    await db.commit()
    await db.refresh(skill)

    return SkillResponse(
        id=str(skill.id),
        name=skill.name,
        category=skill.category,
        proficiency_level=skill.proficiency_level,
        description=skill.description,
        acquired_at=skill.acquired_at.isoformat() if skill.acquired_at else None,
        last_practiced_at=skill.last_practiced_at.isoformat() if skill.last_practiced_at else None,
        metadata=skill.metadata_ or {},
    )
