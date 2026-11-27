"""Browser Security Gateway API (Doc 29 P3)."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.browser_evidence_service import BrowserEvidenceError
from app.services.browser_security_gateway import (
    BrowserSecurityGateway,
    BrowserSecurityGatewayError,
)

router = APIRouter(prefix="/api/v1/browser/security", tags=["browser-security"])


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "sdk") if credential else "sdk"


def _actor_type(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    if credential and str(credential.get("actor_type", "")) == "creator":
        return "creator"
    return "agent"


class InspectRequest(BaseModel):
    text: str = Field(max_length=20000)
    url: str = ""
    task_id: Optional[str] = None
    actor_type: str = "agent"


class QuarantineRequest(BaseModel):
    source_path: str
    original_name: str = ""
    task_id: Optional[str] = None
    actor_type: str = "agent"


class ReleaseRequest(BaseModel):
    quarantine_path: str


@router.post("/inspect")
async def inspect_content(
    payload: InspectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserSecurityGateway(db).inspect_content(
            payload.text,
            url=payload.url,
            task_id=payload.task_id,
            actor=_actor(request),
            actor_type=payload.actor_type,
        )
    except BrowserEvidenceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/permission/{action_type}")
async def check_permission(
    action_type: str,
    request: Request,
    task_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    return await BrowserSecurityGateway(db).check_action(
        action_type,
        task_id=task_id,
        actor=_actor(request),
    )


@router.post("/download/quarantine")
async def quarantine_download(
    payload: QuarantineRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserSecurityGateway(db).quarantine_download(
            payload.source_path,
            original_name=payload.original_name,
            task_id=payload.task_id,
            actor=_actor(request),
            actor_type=payload.actor_type,
        )
    except (BrowserSecurityGatewayError, BrowserEvidenceError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/download/release")
async def release_download(
    payload: ReleaseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserSecurityGateway(db).release_download(
            payload.quarantine_path, actor=_actor(request)
        )
    except BrowserSecurityGatewayError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
