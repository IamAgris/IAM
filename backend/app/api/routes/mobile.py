"""ADB mobile interaction endpoints (opt-in, allowlisted devices)."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.services.mobile_agent import MobileAgentError, MobileAgentService

router = APIRouter(prefix="/api/v1/mobile", tags=["mobile-agent"])


class DeviceRequest(BaseModel):
    device: str


class TapRequest(DeviceRequest):
    x: int
    y: int


class SwipeRequest(TapRequest):
    x2: int
    y2: int


class TypeRequest(DeviceRequest):
    text: str


class ScreenshotRequest(DeviceRequest):
    filename: str


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


@router.get("/policy")
async def policy():  # type: ignore[no-untyped-def]
    return {
        "enabled": settings.mobile_agent_enabled,
        "adb_path": settings.mobile_adb_path,
        "allowed_devices": [
            item.strip() for item in settings.mobile_allowed_devices.split(",") if item.strip()
        ],
    }


@router.post("/devices")
async def devices(request: Request, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    try:
        return await MobileAgentService(db).list_devices(_actor(request))  # type: ignore[no-untyped-call]
    except MobileAgentError as exc:
        raise HTTPException(403, str(exc)) from exc


@router.post("/tap")
async def tap(payload: TapRequest, request: Request, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    try:
        return await MobileAgentService(db).tap(  # type: ignore[no-untyped-call]
            payload.device, payload.x, payload.y, _actor(request)
        )
    except MobileAgentError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/swipe")
async def swipe(payload: SwipeRequest, request: Request, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    try:
        return await MobileAgentService(db).swipe(  # type: ignore[no-untyped-call]
            payload.device, payload.x, payload.y, payload.x2, payload.y2, _actor(request)
        )
    except MobileAgentError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/type")
async def type_text(payload: TypeRequest, request: Request, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    try:
        return await MobileAgentService(db).type_text(  # type: ignore[no-untyped-call]
            payload.device, payload.text, _actor(request)
        )
    except MobileAgentError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/screenshot")
async def screenshot(payload: ScreenshotRequest, request: Request, db=Depends(get_db_session)):  # type: ignore[no-untyped-def]
    try:
        return await MobileAgentService(db).screenshot(  # type: ignore[no-untyped-call]
            payload.device, payload.filename, _actor(request)
        )
    except MobileAgentError as exc:
        raise HTTPException(400, str(exc)) from exc
