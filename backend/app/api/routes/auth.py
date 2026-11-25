"""Scoped API credential management.

The bootstrap endpoint is the only way to create the first credential; it is
protected by a key from the environment, not by a UI. Creator authority (OD-19)
remains email + signed challenge and is never issued as an API key.
"""

import hmac
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_policy import SCOPE_RANK
from app.core.config import settings
from app.core.database import get_db_session
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["api-authentication"])


class CredentialRequest(BaseModel):
    name: str
    scope: str = "user"


class BootstrapRequest(CredentialRequest):
    pass


def _admin(request: Request) -> None:
    credential = getattr(request.state, "credential", None)
    if not credential or credential.get("scope") != "admin":
        raise HTTPException(status_code=403, detail="Admin scope required")


@router.post("/bootstrap", status_code=201)
async def bootstrap(
    request: Request,
    payload: BootstrapRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Create the first credential using the environment bootstrap key."""
    expected = os.environ.get(settings.auth_bootstrap_key_env, "")
    provided = request.headers.get("X-Bootstrap-Key", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Bootstrap is not configured")
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=403, detail="Invalid bootstrap key")
    if payload.scope not in SCOPE_RANK:
        raise HTTPException(status_code=400, detail=f"Unknown scope: {payload.scope}")
    try:
        credential, plaintext = await AuthService(db).create_credential(
            payload.name, payload.scope, "bootstrap"
        )
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": str(credential.id),
        "name": credential.name,
        "scope": credential.scope,
        "key": plaintext,
        "note": "Store this key securely; it is shown once.",
    }


@router.get("/me")
async def me(request: Request):
    credential = getattr(request.state, "credential", None)
    if not credential:
        raise HTTPException(status_code=401, detail="No credential on request")
    return credential


@router.post("/credentials", status_code=201)
async def create_credential(
    request: Request,
    payload: CredentialRequest,
    db: AsyncSession = Depends(get_db_session),
):
    _admin(request)
    if payload.scope not in SCOPE_RANK:
        raise HTTPException(status_code=400, detail=f"Unknown scope: {payload.scope}")
    credential, plaintext = await AuthService(db).create_credential(
        payload.name, payload.scope, request.state.credential["name"]
    )
    return {
        "id": str(credential.id),
        "name": credential.name,
        "scope": credential.scope,
        "key": plaintext,
        "note": "Store this key securely; it is shown once.",
    }


@router.get("/credentials")
async def list_credentials(
    request: Request, db: AsyncSession = Depends(get_db_session)
):
    _admin(request)
    return await AuthService(db).list_credentials()


@router.post("/credentials/{name}/revoke")
async def revoke_credential(
    name: str, request: Request, db: AsyncSession = Depends(get_db_session)
):
    _admin(request)
    if not await AuthService(db).revoke_credential(name):
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"name": name, "revoked": True}
