"""Operator-only encrypted provider-connection credential endpoints (OD-51).

No plaintext secret is ever returned. Registration, rotation and disabling
require a signed Creator authorization through the vault service.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.model_credential_vault import (
    VaultError,
    ModelCredentialVault,
)
from app.services.model_policy import ModelPolicyDenied

router = APIRouter(
    prefix="/api/v1/models/credentials", tags=["model-provider-credentials"]
)


class RegisterKey(BaseModel):
    provider: str
    key_alias: str
    secret: str
    scope: str = "free"
    monthly_limit_usd: Optional[float] = None


class RotateKey(BaseModel):
    secret: str


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "operator")) if credential else "operator"


@router.post("")
async def register(
    payload: RegisterKey,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await ModelCredentialVault(db).register(
            provider=payload.provider,
            key_alias=payload.key_alias,
            secret=payload.secret,
            scope=payload.scope,
            monthly_limit_usd=payload.monthly_limit_usd,
            actor=_actor(request),
        )
    except (VaultError, ModelPolicyDenied) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/health")
async def health(
    provider: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Read-only key health. Never returns ciphertext or plaintext."""
    return {"keys": await ModelCredentialVault(db).health(provider)}


@router.post("/{key_id}/disable")
async def disable(
    key_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await ModelCredentialVault(db).disable(key_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (VaultError, ModelPolicyDenied) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{key_id}/rotate")
async def rotate(
    key_id: str,
    payload: RotateKey,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        return await ModelCredentialVault(db).rotate(
            key_id, secret=payload.secret, actor=_actor(request)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (VaultError, ModelPolicyDenied) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/{key_id}/health")
async def mark_health(
    key_id: str,
    healthy: bool,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Mark a connection healthy/unhealthy for per-key failover."""
    try:
        return await ModelCredentialVault(db).mark_health(key_id, healthy=healthy)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
