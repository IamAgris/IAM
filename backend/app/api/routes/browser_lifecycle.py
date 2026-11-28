"""Browser lifecycle and hardening API (Doc 29 P8)."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.browser_lifecycle import BrowserLifecycleError, BrowserLifecycleService

router = APIRouter(prefix="/api/v1/browser/lifecycle", tags=["browser-lifecycle"])


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "sdk") if credential else "sdk"


class BackupVerifyRequest(BaseModel):
    backup_ref: str


class UpdateRequest(BaseModel):
    component: str
    version: str


class RetireRequest(BaseModel):
    component: str
    reason: str


@router.get("/snapshot")
async def snapshot() -> Dict[str, Any]:
    return BrowserLifecycleService(object()).snapshot()  # type: ignore[arg-type]


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    return await BrowserLifecycleService(db).health()


@router.get("/vulnerabilities")
async def vulnerabilities() -> Dict[str, Any]:
    return BrowserLifecycleService(object()).vulnerability_scan()  # type: ignore[arg-type]


@router.post("/snapshot/record")
async def record_snapshot(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    return await BrowserLifecycleService(db).snapshot_record(_actor(request))


@router.post("/backup")
async def backup(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    return await BrowserLifecycleService(db).backup(_actor(request))


@router.post("/verify-backup")
async def verify_backup(
    payload: BackupVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserLifecycleService(db).verify_backup(
            payload.backup_ref, _actor(request)
        )
    except BrowserLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/update")
async def apply_update(
    payload: UpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserLifecycleService(db).apply_update(
            payload.component, payload.version, _actor(request)
        )
    except BrowserLifecycleError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/retire")
async def retire(
    payload: RetireRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await BrowserLifecycleService(db).retire(
            payload.component, payload.reason, _actor(request)
        )
    except BrowserLifecycleError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/audit")
async def audit_report(
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    return await BrowserLifecycleService(db).audit_report()


@router.get("/performance")
async def performance() -> Dict[str, Any]:
    return BrowserLifecycleService(object()).performance_budget()  # type: ignore[arg-type]
