"""IAM Internet Access and Digital Interaction System routes.

Public exploration is open; consequential actions require owner authorization.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.core.database import get_db_session
from app.services.internetaccess_service import InternetAccessService

router = APIRouter(prefix="/api/v1/internet", tags=["internet-access"])


class SessionRequest(BaseModel):
    purpose: Optional[str] = None


class BrowseRequest(BaseModel):
    url: str
    session_token: Optional[str] = None
    action: str = "navigate"  # navigate, click, type, submit, scroll, screenshot, text, links
    target: Optional[str] = None
    value: Optional[str] = None


class SearchRequest(BaseModel):
    query: str
    max_results: int = 10


class AccountRequest(BaseModel):
    platform: str
    account_identifier: Optional[str] = None
    credential_reference: Optional[str] = None
    account_type: str = "service"
    authorised_by: Optional[str] = None


class RotateCredentialRequest(BaseModel):
    credential_reference: str


class PublishRequest(BaseModel):
    title: str
    content_type: str
    target_platform: Optional[str] = None
    url: Optional[str] = None
    authorised_by: Optional[str] = None


class MonitorRequest(BaseModel):
    target_url: str
    target_type: str = "website"
    check_interval_minutes: int = 60


class FileRequest(BaseModel):
    source_url: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    storage_path: Optional[str] = None
    size_bytes: Optional[int] = None


class PermissionCheckRequest(BaseModel):
    action_type: str


@router.post("/initialize")
async def initialize(db=Depends(get_db_session)):
    """Initialize default internet permission gates."""
    service = InternetAccessService(db)
    await service.initialize_permissions()
    return {"status": "initialized"}


@router.get("/permissions")
async def list_permissions(db=Depends(get_db_session)):
    """List all internet permission gates."""
    from app.models.internetaccess import InternetPermission
    from sqlalchemy import select
    result = await db.execute(select(InternetPermission))
    return [
        {
            "action_type": p.action_type,
            "category": p.category,
            "is_autonomous": p.is_autonomous,
            "requires_creator_authorization": p.requires_creator_authorization,
            "description": p.description,
        }
        for p in result.scalars().all()
    ]


@router.post("/permissions/check")
async def check_permission(request: PermissionCheckRequest, db=Depends(get_db_session)):
    """Check whether an internet action is permitted."""
    service = InternetAccessService(db)
    return await service.check_permission(request.action_type)


@router.post("/sessions")
async def create_session(request: SessionRequest, db=Depends(get_db_session)):
    """Create a persistent browsing session."""
    service = InternetAccessService(db)
    return await service.create_session(request.purpose)


@router.delete("/sessions/{token}")
async def close_session(token: str, db=Depends(get_db_session)):
    """Close a browsing session."""
    service = InternetAccessService(db)
    ok = await service.close_session(token)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "closed"}


@router.post("/browse")
async def browse(request: BrowseRequest, db=Depends(get_db_session)):
    """Browse or interact with the internet (public exploration is autonomous)."""
    service = InternetAccessService(db)
    return await service.browse(
        request.url, request.session_token, request.action,
        request.target, request.value,
    )


@router.post("/search")
async def search(request: SearchRequest, db=Depends(get_db_session)):
    """Search the web (autonomous public exploration)."""
    service = InternetAccessService(db)
    return await service.search(request.query, request.max_results)


@router.post("/accounts")
async def register_account(request: AccountRequest, db=Depends(get_db_session)):
    """Register an online account (requires owner authorization)."""
    service = InternetAccessService(db)
    result = await service.register_account(
        request.platform, request.account_identifier, request.credential_reference,
        request.account_type, request.authorised_by,
    )
    if "error" in result:
        raise HTTPException(status_code=403, detail=result)
    return result


@router.get("/accounts")
async def list_accounts(db=Depends(get_db_session)):
    """List account metadata; credential values are never returned."""
    return await InternetAccessService(db).list_accounts()


@router.post("/accounts/{account_id}/rotate")
async def rotate_account_credential(
    account_id: str,
    request: RotateCredentialRequest,
    db=Depends(get_db_session),
):
    try:
        return await InternetAccessService(db).rotate_account_credential(
            account_id, request.credential_reference, "sdk"
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/accounts/{account_id}/close")
async def close_account(account_id: str, db=Depends(get_db_session)):
    try:
        return await InternetAccessService(db).close_account(account_id, "sdk")
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/publish")
async def publish_content(request: PublishRequest, db=Depends(get_db_session)):
    """Publish content (requires owner authorization)."""
    service = InternetAccessService(db)
    result = await service.publish_content(
        request.title, request.content_type, request.target_platform,
        request.url, request.authorised_by,
    )
    if "error" in result:
        raise HTTPException(status_code=403, detail=result)
    return result


@router.post("/monitor")
async def add_monitored_target(request: MonitorRequest, db=Depends(get_db_session)):
    """Add a website/service to monitor."""
    service = InternetAccessService(db)
    return await service.add_monitored_target(
        request.target_url, request.target_type, request.check_interval_minutes
    )


@router.post("/files")
async def record_file(request: FileRequest, db=Depends(get_db_session)):
    """Record a retrieved file for scanning and analysis."""
    service = InternetAccessService(db)
    return await service.record_retrieved_file(
        request.source_url, request.filename, request.content_type,
        request.storage_path, request.size_bytes,
    )


@router.get("/events")
async def get_events(limit: int = 100, db=Depends(get_db_session)):
    """Get the internet activity audit trail."""
    service = InternetAccessService(db)
    return await service.get_events(limit)
