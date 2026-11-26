"""Model independence API — comparisons, signed adoption, portability, fallback."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.model_independence import (
    ADOPT_ACTION,
    FALLBACK_ACTION,
    PORTABLE_SCOPES,
    SCORE_WEIGHTS,
    ModelIndependenceError,
    ModelIndependenceService,
)

router = APIRouter(prefix="/api/v1/model-independence", tags=["model-independence"])


class ComparisonCreate(BaseModel):
    model_name: str
    provider: str
    model_id: str
    capabilities_tested: List[str] = Field(default_factory=list)
    scores: Dict[str, Any] = Field(default_factory=dict)


class ExportRequest(BaseModel):
    scope: List[str] = Field(default_factory=lambda: sorted(PORTABLE_SCOPES))


class FallbackRequest(BaseModel):
    primary_model: str
    fallback_model: str
    fallback_provider: str


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "iam") if credential else "iam"


@router.get("/policy")
async def policy():
    return {
        "protected_core_actions": [ADOPT_ACTION, FALLBACK_ACTION],
        "requires_signed_creator_authorization": True,
        "score_weights": SCORE_WEIGHTS,
        "portable_scopes": sorted(PORTABLE_SCOPES),
        "private_content_exported": False,
    }


@router.post("/comparisons")
async def record_comparison(
    payload: ComparisonCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    return await ModelIndependenceService(db).record_comparison(
        model_name=payload.model_name,
        provider=payload.provider,
        model_id=payload.model_id,
        capabilities_tested=payload.capabilities_tested,
        scores=payload.scores,
        actor=_actor(request),
    )


@router.get("/comparisons")
async def list_comparisons(db: AsyncSession = Depends(get_db_session)):
    return await ModelIndependenceService(db).comparisons()


@router.post("/comparisons/{comparison_id}/adopt")
async def adopt_comparison(
    comparison_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ModelIndependenceService(db).adopt(comparison_id, _actor(request))
    except ModelIndependenceError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/exports")
async def export_portability(
    payload: ExportRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ModelIndependenceService(db).export(payload.scope, _actor(request))
    except ModelIndependenceError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/exports")
async def list_exports(db: AsyncSession = Depends(get_db_session)):
    return await ModelIndependenceService(db).exports()


@router.post("/fallback")
async def set_fallback(
    payload: FallbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ModelIndependenceService(db).set_fallback(
            payload.primary_model,
            payload.fallback_model,
            payload.fallback_provider,
            _actor(request),
        )
    except ModelIndependenceError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.get("/fallback")
async def active_fallback(db: AsyncSession = Depends(get_db_session)):
    return await ModelIndependenceService(db).active_fallback()
