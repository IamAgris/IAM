"""Global access routes — anonymous sessions, GeoIP, isolated conversations, privacy"""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.core.database import get_db_session
from app.services.globalaccess_service import GlobalAccessService

router = APIRouter(prefix="/api/v1/access", tags=["global-access"])


class SessionCreateRequest(BaseModel):
    visitor_token: Optional[str] = None
    mode: str = "focus"


class MessageRequest(BaseModel):
    session_token: str
    content: str
    role: str = "user"
    thread_id: Optional[str] = None


class ModeRequest(BaseModel):
    session_token: str
    mode: str


class ConsentRequest(BaseModel):
    visitor_id: str
    consent_type: str
    granted: bool
    retention_days: Optional[int] = None


class MemoryPermissionRequest(BaseModel):
    visitor_id: str
    allow_session_memory: Optional[bool] = None
    allow_anonymous_memory: Optional[bool] = None
    allow_shared_knowledge: Optional[bool] = None


class DataCorrectionRequest(BaseModel):
    preferences: Dict[str, Any] = {}
    memory_permissions: Dict[str, bool] = {}


class LocationCorrectionRequest(BaseModel):
    session_token: str
    country: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None


@router.post("/visitors")
async def create_visitor(request: SessionCreateRequest, db=Depends(get_db_session)):
    """Get or create an anonymous visitor identity (no registration)."""
    service = GlobalAccessService(db)
    return await service.create_or_get_visitor(request.visitor_token)


@router.post("/sessions")
async def create_session(
    request: SessionCreateRequest,
    http_request: Request,
    db=Depends(get_db_session),
):
    """Create an isolated session. GeoIP resolved server-side from request IP."""
    service = GlobalAccessService(db)
    visitor = await service.create_or_get_visitor(request.visitor_token)
    ip_address = http_request.client.host if http_request.client else None
    forwarded = http_request.headers.get("x-forwarded-for")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    session = await service.create_session(
        visitor["id"], mode=request.mode, ip_address=ip_address, resolve_geo=True
    )
    return {**session, "visitor_token": visitor["visitor_token"]}


@router.get("/sessions/{session_token}/context")
async def get_session_context(session_token: str, db=Depends(get_db_session)):
    """Get isolated context for a session (location, permissions, mode)."""
    service = GlobalAccessService(db)
    context = await service.get_session_context(session_token)
    if not context:
        raise HTTPException(status_code=404, detail="Session not found")
    return context


@router.post("/messages")
async def add_message(request: MessageRequest, db=Depends(get_db_session)):
    """Store a message in this session's private conversation only."""
    service = GlobalAccessService(db)
    result = await service.add_message(
        request.session_token, request.role, request.content,
        request.thread_id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.get("/sessions/{session_token}/messages")
async def get_messages(
    session_token: str,
    thread_id: Optional[str] = None,
    limit: int = 50,
    db=Depends(get_db_session),
):
    """Get this session's messages — strict isolation, never another visitor's."""
    service = GlobalAccessService(db)
    return await service.get_thread_messages(session_token, thread_id, limit)


@router.patch("/sessions/mode")
async def set_mode(request: ModeRequest, db=Depends(get_db_session)):
    """Set Focus / Recall / Create mode for a session."""
    service = GlobalAccessService(db)
    ok = await service.set_session_mode(request.session_token, request.mode)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid mode or session")
    return {"session_token": request.session_token, "mode": request.mode}


@router.post("/consent")
async def set_consent(request: ConsentRequest, db=Depends(get_db_session)):
    """Record privacy consent."""
    service = GlobalAccessService(db)
    return await service.set_consent(
        request.visitor_id, request.consent_type, request.granted, request.retention_days
    )


@router.post("/memory-permissions")
async def set_memory_permission(request: MemoryPermissionRequest, db=Depends(get_db_session)):
    """Control whether visitor data enters any memory layer."""
    service = GlobalAccessService(db)
    return await service.set_memory_permission(
        request.visitor_id,
        request.allow_session_memory,
        request.allow_anonymous_memory,
        request.allow_shared_knowledge,
    )


@router.patch("/location")
async def correct_location(request: LocationCorrectionRequest, db=Depends(get_db_session)):
    """Visitors can correct estimated location/language."""
    service = GlobalAccessService(db)
    ok = await service.correct_location(
        request.session_token, request.country, request.language, request.timezone
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "corrected"}


@router.get("/visitors/{visitor_token}/data")
async def inspect_visitor_data(visitor_token: str, db=Depends(get_db_session)):
    """OD-05: visitors can inspect all data held under their token."""
    data = await GlobalAccessService(db).inspect_visitor_data(visitor_token)
    if not data:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return data


@router.patch("/visitors/{visitor_token}/data")
async def correct_visitor_data(
    visitor_token: str,
    request: DataCorrectionRequest,
    db=Depends(get_db_session),
):
    """OD-05: visitors can correct preferences and memory permissions."""
    ok = await GlobalAccessService(db).correct_visitor_data(
        visitor_token,
        preferences=request.preferences,
        memory_permissions=request.memory_permissions,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return {"status": "corrected"}


@router.delete("/visitors/{visitor_token}")
async def delete_visitor_data(visitor_token: str, db=Depends(get_db_session)):
    """Honour data deletion requests — removes all visitor data."""
    service = GlobalAccessService(db)
    ok = await service.delete_visitor_data(visitor_token)
    if not ok:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return {"status": "deleted"}
