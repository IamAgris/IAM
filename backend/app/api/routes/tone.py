"""Doc 17 / OD-33: tone and influence analysis routes (defensive only)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.core.database import get_db_session
from app.services.tone_service import ToneService

router = APIRouter(prefix="/api/v1/tone", tags=["tone-intelligence"])


class AnalyseRequest(BaseModel):
    text: str
    source_type: str = "text"


class DiscussionRequest(BaseModel):
    texts: List[str]


class RecordRequest(BaseModel):
    source_type: str = "text"
    content_summary: str


@router.post("/analyze")
async def analyse(request: AnalyseRequest):
    """Interpret tone and influence patterns as possibilities, not diagnoses."""
    return ToneService().analyse_text(request.text)


@router.post("/discussion")
async def analyse_discussion(request: DiscussionRequest):
    """Analyse a discussion and flag possible changes in tone."""
    return ToneService().analyse_discussion(request.texts)


@router.post("/records")
async def record_analysis(request: RecordRequest, db=Depends(get_db_session)):
    """Persist an analysis as evidence with a caveat and confidence marker."""
    try:
        return await ToneService(db).record_analysis(request.source_type, request.content_summary)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/records")
async def list_analyses(limit: int = 50, db=Depends(get_db_session)):
    """List stored tone analyses."""
    return await ToneService(db).list_analyses(limit)
