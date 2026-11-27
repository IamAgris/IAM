"""Legacy owner authorization records — historical/read-only authority view.

OD-03/OD-04 removed standing owner grants. Creation is disabled; checks always
fail closed; existing rows can only be listed and revoked during cleanup.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.core.database import get_db_session
from app.services.ownerauth_service import LegacyAuthorityError, OwnerAuthService

router = APIRouter(prefix="/api/v1/owner", tags=["owner-authorization"])


class GrantRequest(BaseModel):
    action_type: str
    max_authority_level: str = "4"
    spending_limit_usd: Optional[float] = None
    can_create_accounts: bool = False
    can_publish_externally: bool = False
    can_modify_own_security: bool = False
    scope: Optional[Dict[str, Any]] = None
    granted_by: str = "owner"
    expires_at: Optional[str] = None


class CheckRequest(BaseModel):
    action_type: str
    requested_level: str = "1"


@router.post("/authorizations")
async def grant(request: GrantRequest, db: Any = Depends(get_db_session)) -> Any:
    """Retired: standing grants cannot recreate a second authority path."""
    try:
        await OwnerAuthService(db).grant_authorization(
            request.action_type, request.max_authority_level, request.spending_limit_usd,
            request.can_create_accounts, request.can_publish_externally,
            request.can_modify_own_security, request.scope, request.granted_by, request.expires_at,
        )
    except LegacyAuthorityError as exc:
        raise HTTPException(410, str(exc)) from exc
    raise HTTPException(410, "legacy owner grants are disabled")


@router.get("/authorizations")
async def list_authorizations(db: Any = Depends(get_db_session)) -> Any:
    return await OwnerAuthService(db).list_authorizations()


@router.post("/authorizations/check")
async def check(request: CheckRequest, db: Any = Depends(get_db_session)) -> Any:
    """Always fails closed; legacy rows are not authority (OD-03/OD-04)."""
    return await OwnerAuthService(db).check_authorization(
        request.action_type, request.requested_level
    )


@router.delete("/authorizations/{authorization_id}")
async def revoke(authorization_id: str, db: Any = Depends(get_db_session)) -> dict[str, str]:
    if not await OwnerAuthService(db).revoke_authorization(authorization_id):
        raise HTTPException(404, "Authorization not found")
    return {"status": "revoked"}
