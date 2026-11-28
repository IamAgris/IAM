"""Workspace manager API — controlled lifecycle for isolated dev environments."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.services.workspaces.errors import WorkspaceError
from app.services.workspaces.providers import provider_statuses
from app.services.workspaces.service import (
    SUPPORTED_PROVIDERS,
    WorkspaceService,
)

router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])


class WorkspaceCreate(BaseModel):
    name: str
    project_id: Optional[str] = None
    provider: str = "local"
    credential_env_var: Optional[str] = None


class ExecuteRequest(BaseModel):
    command: str


class CredentialCreate(BaseModel):
    purpose: str
    secret_env_var: str
    scopes: Dict[str, Any] = {}
    ttl_seconds: Optional[int] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "iam") if credential else "iam"


def _fail(exc: WorkspaceError) -> HTTPException:
    return HTTPException(status_code=403, detail=str(exc))


@router.get("/policy")
async def policy():  # type: ignore[no-untyped-def]
    return {
        "enabled": settings.workspace_enabled,
        "adapter": settings.workspace_adapter,
        "default_adapter": "stub",
        "supported_providers": list(SUPPORTED_PROVIDERS),
        "providers": [status.as_dict() for status in provider_statuses()],  # type: ignore[no-untyped-call]
        "credential_ttl_seconds": settings.workspace_credential_ttl_seconds,
        "isolation": {
            "core_access": False,
            "network": "none",
            "read_only_protected": True,
            "non_root": True,
            "no_new_privileges": True,
        },
        "credentials": "environment-variable names only; never secret values",
        "execution_requires_active_workspace": True,
    }


@router.post("")
async def create_workspace(  # type: ignore[no-untyped-def]
    payload: WorkspaceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WorkspaceService(db).create(
            name=payload.name,
            project_id=payload.project_id,
            provider=payload.provider,
            credential_env_var=payload.credential_env_var,
            actor=_actor(request),
        )
    except WorkspaceError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(400, "invalid project identifier") from exc


@router.get("")
async def list_workspaces(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await WorkspaceService(db).list()


@router.post("/{workspace_id}/start")
async def start_workspace(  # type: ignore[no-untyped-def]
    workspace_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WorkspaceService(db).start(workspace_id, _actor(request))
    except WorkspaceError as exc:
        raise _fail(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{workspace_id}/execute")
async def execute_in_workspace(  # type: ignore[no-untyped-def]
    workspace_id: str,
    payload: ExecuteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WorkspaceService(db).execute(
            workspace_id, payload.command, _actor(request)
        )
    except WorkspaceError as exc:
        raise _fail(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{workspace_id}/save")
async def save_workspace(  # type: ignore[no-untyped-def]
    workspace_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WorkspaceService(db).save(workspace_id, _actor(request))
    except WorkspaceError as exc:
        raise _fail(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{workspace_id}/credentials")
async def issue_workspace_credential(  # type: ignore[no-untyped-def]
    workspace_id: str,
    payload: CredentialCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Issue a short-lived, host-scoped credential reference (never a value)."""
    try:
        return await WorkspaceService(db).issue_credential(
            workspace_id,
            purpose=payload.purpose,
            secret_env_var=payload.secret_env_var,
            scopes=payload.scopes,
            ttl_seconds=payload.ttl_seconds,
            actor=_actor(request),
        )
    except WorkspaceError as exc:
        raise _fail(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{workspace_id}/credentials")
async def list_workspace_credentials(  # type: ignore[no-untyped-def]
    workspace_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WorkspaceService(db).list_credentials(workspace_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/{workspace_id}/credentials/{credential_id}")
async def revoke_workspace_credential(  # type: ignore[no-untyped-def]
    workspace_id: str,
    credential_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WorkspaceService(db).revoke_credential(
            workspace_id, credential_id, _actor(request)
        )
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, "invalid credential identifier") from exc


@router.delete("/{workspace_id}")
async def destroy_workspace(  # type: ignore[no-untyped-def]
    workspace_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WorkspaceService(db).destroy(workspace_id, _actor(request))
    except WorkspaceError as exc:
        raise _fail(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
