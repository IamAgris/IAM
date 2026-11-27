"""TIPS API — Tor status, sessions, circuits and kill switch (Doc 29 P5)."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.services.tor_intelligence import TorManager, TorUnavailable

router = APIRouter(prefix="/api/v1/tor", tags=["tor-privacy"])

# Process-local Tor state: sessions and kill switch must be shared between
# requests. It is never persisted and never shared across deployments.
_manager: Optional[TorManager] = None


def get_manager() -> TorManager:
    global _manager
    if _manager is None:
        from app.core.database import get_session_factory

        _manager = TorManager(get_session_factory()())
    return _manager


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "sdk") if credential else "sdk"


class EgressRequest(BaseModel):
    session_id: Optional[str] = None
    url: str


class SessionRequest(BaseModel):
    actor_type: str = "agent"
    task_id: Optional[str] = None


@router.get("/status")
async def status(manager: TorManager = Depends(get_manager)) -> Dict[str, Any]:
    return await manager.status()


@router.post("/sessions/{session_id}")
async def open_session(
    session_id: str,
    payload: SessionRequest,
    request: Request,
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    try:
        return await manager.open_session(
            session_id,
            actor=_actor(request),
            actor_type=payload.actor_type,
            task_id=payload.task_id,
        )
    except TorUnavailable as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.delete("/sessions/{session_id}")
async def close_session(
    session_id: str,
    request: Request,
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    closed = await manager.close_session(session_id, actor=_actor(request))
    return {"session_id": session_id, "closed": closed}


@router.get("/circuits")
async def circuits(manager: TorManager = Depends(get_manager)) -> Dict[str, Any]:
    try:
        return await manager.circuits()
    except TorUnavailable as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/identity/new")
async def new_identity(
    request: Request,
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    try:
        return await manager.new_identity(actor=_actor(request))
    except TorUnavailable as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/killswitch")
async def killswitch_status(manager: TorManager = Depends(get_manager)) -> Dict[str, Any]:
    return {"kill_switch": manager.privacy.kill_switch}


@router.post("/killswitch")
async def engage_killswitch(manager: TorManager = Depends(get_manager)) -> Dict[str, Any]:
    return manager.privacy.engage()


@router.delete("/killswitch")
async def release_killswitch(
    request: Request,
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    return manager.privacy.release(_actor(request))


@router.post("/egress/check")
async def check_egress(
    payload: EgressRequest,
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    try:
        manager._require_enabled()
    except TorUnavailable as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return manager.privacy.check_egress(payload.session_id, payload.url)


@router.post("/terminate-all")
async def terminate_all(
    request: Request,
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    return await manager.terminate_all(actor=_actor(request))
