"""Human Assistance & Intervention System endpoints."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.human_assistance import AssistanceError, HumanAssistanceService

router = APIRouter(prefix="/api/v1/assistance", tags=["human-assistance"])


class AssistanceCreate(BaseModel):
    level: str
    reason: str
    context: Dict[str, Any] = Field(default_factory=dict)
    task_ref: Optional[str] = None


class ResolveRequest(BaseModel):
    resolved_by: str
    note: str = ""


class EscalateRequest(BaseModel):
    reason: str = ""


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


@router.get("/levels")
async def levels():  # type: ignore[no-untyped-def]
    from app.services.human_assistance import LEVELS

    return LEVELS


@router.post("/requests")
async def request_assistance(  # type: ignore[no-untyped-def]
    payload: AssistanceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await HumanAssistanceService(db).request(
            level=payload.level,
            reason=payload.reason,
            context=payload.context,
            task_ref=payload.task_ref,
            actor=_actor(request),
        )
    except AssistanceError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/requests")
async def list_requests(  # type: ignore[no-untyped-def]
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await HumanAssistanceService(db).list(status)
    except AssistanceError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/requests/{request_id}/resolve")
async def resolve_request(  # type: ignore[no-untyped-def]
    request_id: str,
    payload: ResolveRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await HumanAssistanceService(db).resolve(
            request_id, payload.resolved_by, _actor(request), payload.note
        )
    except AssistanceError as exc:
        raise HTTPException(400, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/requests/{request_id}/escalate")
async def escalate_request(  # type: ignore[no-untyped-def]
    request_id: str,
    payload: EscalateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await HumanAssistanceService(db).escalate(
            request_id, _actor(request), payload.reason
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
