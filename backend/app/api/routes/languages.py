"""Language learning routes - track proficiency and progress"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db_session
from app.models.memory import LanguageProfile

router = APIRouter(prefix="/api/v1/languages", tags=["languages"])


class LanguageProfileCreate(BaseModel):
    language_code: str  # ISO 639-1
    vocabulary_level: int = 0
    grammar_level: int = 0
    reading_comprehension: int = 0
    listening_comprehension: int = 0
    writing_ability: int = 0
    conversational_ability: int = 0
    pronunciation_level: int = 0


class LanguageProfileUpdate(BaseModel):
    vocabulary_level: Optional[int] = None
    grammar_level: Optional[int] = None
    reading_comprehension: Optional[int] = None
    listening_comprehension: Optional[int] = None
    writing_ability: Optional[int] = None
    conversational_ability: Optional[int] = None
    pronunciation_level: Optional[int] = None


class LanguageProfileResponse(BaseModel):
    id: str
    language_code: str
    vocabulary_level: int
    grammar_level: int
    reading_comprehension: int
    listening_comprehension: int
    writing_ability: int
    conversational_ability: int
    pronunciation_level: int
    updated_at: Optional[str]

    class Config:
        from_attributes = True


def _clamp(value: int) -> int:
    return max(0, min(100, value))


@router.get("/", response_model=List[LanguageProfileResponse])
async def list_languages(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """List all language profiles."""
    result = await db.execute(select(LanguageProfile))
    profiles = result.scalars().all()
    return [
        LanguageProfileResponse(
            id=str(p.id),
            language_code=p.language_code,  # type: ignore[arg-type]
            vocabulary_level=p.vocabulary_level,  # type: ignore[arg-type]
            grammar_level=p.grammar_level,  # type: ignore[arg-type]
            reading_comprehension=p.reading_comprehension,  # type: ignore[arg-type]
            listening_comprehension=p.listening_comprehension,  # type: ignore[arg-type]
            writing_ability=p.writing_ability,  # type: ignore[arg-type]
            conversational_ability=p.conversational_ability,  # type: ignore[arg-type]
            pronunciation_level=p.pronunciation_level,  # type: ignore[arg-type]
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )
        for p in profiles
    ]


@router.post("/", response_model=LanguageProfileResponse)
async def create_language_profile(  # type: ignore[no-untyped-def]
    profile: LanguageProfileCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create or initialize a language learning profile."""
    lang = LanguageProfile(
        language_code=profile.language_code,
        vocabulary_level=_clamp(profile.vocabulary_level),
        grammar_level=_clamp(profile.grammar_level),
        reading_comprehension=_clamp(profile.reading_comprehension),
        listening_comprehension=_clamp(profile.listening_comprehension),
        writing_ability=_clamp(profile.writing_ability),
        conversational_ability=_clamp(profile.conversational_ability),
        pronunciation_level=_clamp(profile.pronunciation_level),
    )
    db.add(lang)
    await db.commit()
    await db.refresh(lang)

    return LanguageProfileResponse(
        id=str(lang.id),
        language_code=lang.language_code,  # type: ignore[arg-type]
        vocabulary_level=lang.vocabulary_level,  # type: ignore[arg-type]
        grammar_level=lang.grammar_level,  # type: ignore[arg-type]
        reading_comprehension=lang.reading_comprehension,  # type: ignore[arg-type]
        listening_comprehension=lang.listening_comprehension,  # type: ignore[arg-type]
        writing_ability=lang.writing_ability,  # type: ignore[arg-type]
        conversational_ability=lang.conversational_ability,  # type: ignore[arg-type]
        pronunciation_level=lang.pronunciation_level,  # type: ignore[arg-type]
        updated_at=lang.updated_at.isoformat() if lang.updated_at else None,
    )


@router.patch("/{language_code}", response_model=LanguageProfileResponse)
async def update_language_progress(  # type: ignore[no-untyped-def]
    language_code: str,
    update: LanguageProfileUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update language proficiency levels."""
    result = await db.execute(
        select(LanguageProfile).where(LanguageProfile.language_code == language_code)
    )
    lang = result.scalar_one_or_none()
    if not lang:
        raise HTTPException(status_code=404, detail="Language profile not found")

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(lang, key):
            setattr(lang, key, _clamp(value))

    await db.commit()
    await db.refresh(lang)

    return LanguageProfileResponse(
        id=str(lang.id),
        language_code=lang.language_code,  # type: ignore[arg-type]
        vocabulary_level=lang.vocabulary_level,  # type: ignore[arg-type]
        grammar_level=lang.grammar_level,  # type: ignore[arg-type]
        reading_comprehension=lang.reading_comprehension,  # type: ignore[arg-type]
        listening_comprehension=lang.listening_comprehension,  # type: ignore[arg-type]
        writing_ability=lang.writing_ability,  # type: ignore[arg-type]
        conversational_ability=lang.conversational_ability,  # type: ignore[arg-type]
        pronunciation_level=lang.pronunciation_level,  # type: ignore[arg-type]
        updated_at=lang.updated_at.isoformat() if lang.updated_at else None,
    )
