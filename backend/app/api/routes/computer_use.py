"""Visual computer-use endpoints (opt-in, permission-gated)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.services.computer_use import ComputerUseError, ComputerUseService

router = APIRouter(prefix="/api/v1/uwaie/computer", tags=["computer-use"])


class SessionRequest(BaseModel):
    session_token: str


class ClickRequest(SessionRequest):
    x: int
    y: int


class TypeRequest(SessionRequest):
    text: str


class PressRequest(SessionRequest):
    key: str


class ScrollRequest(ClickRequest):
    delta: int


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


@router.get("/policy")
async def policy():
    return {"enabled": settings.uwai_computer_use_enabled, "permission": "uwai_computer_use"}


@router.post("/screenshot")
async def screenshot(payload: SessionRequest, request: Request, db=Depends(get_db_session)):
    try:
        return await ComputerUseService(db).screenshot(payload.session_token, _actor(request))
    except ComputerUseError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.post("/click")
async def click(payload: ClickRequest, request: Request, db=Depends(get_db_session)):
    try:
        return await ComputerUseService(db).click(
            payload.session_token, payload.x, payload.y, _actor(request)
        )
    except ComputerUseError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/type")
async def type_text(payload: TypeRequest, request: Request, db=Depends(get_db_session)):
    try:
        return await ComputerUseService(db).type_text(
            payload.session_token, payload.text, _actor(request)
        )
    except ComputerUseError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/press")
async def press(payload: PressRequest, request: Request, db=Depends(get_db_session)):
    try:
        return await ComputerUseService(db).press(
            payload.session_token, payload.key, _actor(request)
        )
    except ComputerUseError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/scroll")
async def scroll(payload: ScrollRequest, request: Request, db=Depends(get_db_session)):
    try:
        return await ComputerUseService(db).scroll(
            payload.session_token, payload.x, payload.y, payload.delta, _actor(request)
        )
    except ComputerUseError as exc:
        raise HTTPException(400, str(exc)) from exc
