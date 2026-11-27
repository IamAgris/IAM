"""TIPS API — Tor status, sessions, circuits and kill switch (Doc 29 P5)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.tor_intelligence import TorManager, TorUnavailable
from app.services.tor_privacy import (
    OnionServiceIntelligence,
    TorCreatorControls,
    TorEmergencyController,
    TorFilePipeline,
    TorPrivacyError,
    validate_onion_address,
)

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


class OnionObserveRequest(BaseModel):
    address: str
    claimed_operator: Optional[str] = None
    source_urls: List[str] = []
    task_id: Optional[str] = None


class OnionAssessRequest(BaseModel):
    address: str
    task_id: Optional[str] = None


class TorFileRequest(BaseModel):
    source_path: str
    original_name: str = ""
    licence_source_id: Optional[str] = None
    task_id: Optional[str] = None


class OnionAccessRequest(BaseModel):
    enabled: bool


class BandwidthRequest(BaseModel):
    kbps: int


class DurationRequest(BaseModel):
    seconds: int


@router.post("/onion/observe")
async def observe_onion(
    payload: OnionObserveRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    if not validate_onion_address(payload.address):
        raise HTTPException(status_code=400, detail="invalid V3 onion address")
    return await OnionServiceIntelligence(db).observe(
        payload.address,
        claimed_operator=payload.claimed_operator,
        source_urls=payload.source_urls,
        task_id=payload.task_id,
    )


@router.post("/onion/assess")
async def assess_onion(
    payload: OnionAssessRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await OnionServiceIntelligence(db).assess(
            payload.address, task_id=payload.task_id
        )
    except TorPrivacyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/files/quarantine")
async def quarantine_tor_file(
    payload: TorFileRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    result = await TorFilePipeline(db).process(
        payload.source_path,
        original_name=payload.original_name,
        licence_source_id=payload.licence_source_id,
        task_id=payload.task_id,
        actor=_actor(request),
    )
    return result


@router.get("/creator/policy")
async def creator_policy(manager: TorManager = Depends(get_manager)) -> Dict[str, Any]:
    return TorCreatorControls(manager).policy()


@router.post("/creator/onion")
async def set_onion_access(
    payload: OnionAccessRequest,
    request: Request,
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    return TorCreatorControls(manager).set_onion_access(
        payload.enabled, _actor(request)
    )


@router.post("/creator/bandwidth")
async def set_bandwidth(
    payload: BandwidthRequest,
    request: Request,
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    try:
        return TorCreatorControls(manager).set_bandwidth_limit(
            payload.kbps, _actor(request)
        )
    except TorPrivacyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/creator/duration")
async def set_duration(
    payload: DurationRequest,
    request: Request,
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    try:
        return TorCreatorControls(manager).set_session_duration(
            payload.seconds, _actor(request)
        )
    except TorPrivacyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/creator/sessions")
async def creator_sessions(
    manager: TorManager = Depends(get_manager),
) -> List[Dict[str, Any]]:
    return TorCreatorControls(manager).view_sessions()


@router.post("/emergency/stop")
async def emergency_stop(
    request: Request,
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    return await TorEmergencyController(manager).stop(actor="creator")


@router.post("/emergency/cleanup")
async def emergency_cleanup(
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    return await TorEmergencyController(manager).cleanup_after_crash()


@router.get("/emergency/suspicious")
async def suspicious_connections(
    manager: TorManager = Depends(get_manager),
) -> Dict[str, Any]:
    return await TorEmergencyController(manager).suspicious_connections()
