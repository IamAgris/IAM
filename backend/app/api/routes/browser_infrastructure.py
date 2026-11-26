"""Browser & Device Infrastructure API routes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.browser_infrastructure_service import (
    BrowserInfrastructureError,
    BrowserInfrastructureService,
)

router = APIRouter(prefix="/api/v1/web/browser", tags=["browser-infrastructure"])


class BrowserCreate(BaseModel):
    name: str
    browser_type: str
    mode: str = "headless"
    profile_name: Optional[str] = None
    remote_endpoint: Optional[str] = None
    device_serial: Optional[str] = None
    resource_allocation: Dict[str, Any] = Field(default_factory=dict)
    concurrent_session_limit: int = Field(default=1, ge=1, le=100)


class BrowserAllocationUpdate(BaseModel):
    concurrent_session_limit: Optional[int] = Field(None, ge=1, le=100)
    resource_allocation: Optional[Dict[str, Any]] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _fail(exc: BrowserInfrastructureError) -> HTTPException:
    return HTTPException(400, str(exc))


@router.post("")
async def create_browser(
    payload: BrowserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new browser infrastructure record."""
    try:
        return await BrowserInfrastructureService(db).create(
            name=payload.name,
            browser_type=payload.browser_type,
            mode=payload.mode,
            profile_name=payload.profile_name,
            remote_endpoint=payload.remote_endpoint,
            device_serial=payload.device_serial,
            resource_allocation=payload.resource_allocation,
            concurrent_session_limit=payload.concurrent_session_limit,
            actor=_actor(request),
        )
    except BrowserInfrastructureError as exc:
        raise _fail(exc) from exc


@router.get("")
async def list_browsers(
    is_available: Optional[bool] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List browser infrastructure records."""
    return await BrowserInfrastructureService(db).list(is_available=is_available)


@router.get("/{browser_id}")
async def get_browser(browser_id: str, db: AsyncSession = Depends(get_db_session)):
    """Get a single browser infrastructure record by ID."""
    try:
        return await BrowserInfrastructureService(db).get(browser_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.patch("/{browser_id}/health")
async def update_health(
    browser_id: str,
    health_status: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Update browser health status."""
    try:
        return await BrowserInfrastructureService(db).update_health(
            browser_id, health_status=health_status, actor=_actor(request)
        )
    except BrowserInfrastructureError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.patch("/{browser_id}/allocation")
async def update_allocation(
    browser_id: str,
    payload: BrowserAllocationUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Update browser resource allocation."""
    try:
        return await BrowserInfrastructureService(db).update_allocation(
            browser_id,
            concurrent_session_limit=payload.concurrent_session_limit,
            resource_allocation=payload.resource_allocation,
            actor=_actor(request),
        )
    except BrowserInfrastructureError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/{browser_id}")
async def delete_browser(
    browser_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Delete browser infrastructure record."""
    try:
        return await BrowserInfrastructureService(db).delete(browser_id, actor=_actor(request))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc