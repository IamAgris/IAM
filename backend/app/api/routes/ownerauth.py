"""Owner authorization routes — human-controlled authority grants.

IAM can never write here. Every grant is an explicit owner action.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.core.database import get_db_session
from app.services.ownerauth_service import OwnerAuthService

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
async def grant(request: GrantRequest, db=Depends(get_db_session)):
    """Owner grants an authorization. IAM can never call this itself."""
    service = OwnerAuthService(db)
    return await service.grant_authorization(
        request.action_type, request.max_authority_level,
        request.spending_limit_usd, request.can_create_accounts,
        request.can_publish_externally, request.can_modify_own_security,
        request.scope, request.granted_by, request.expires_at,
    )


@router.get("/authorizations")
async def list_authorizations(db=Depends(get_db_session)):
    """List owner-granted authorizations."""
    service = OwnerAuthService(db)
    return await service.list_authorizations()


@router.post("/authorizations/check")
async def check_authorization(request: CheckRequest, db=Depends(get_db_session)):
    """IAM checks whether owner authorized an action."""
    service = OwnerAuthService(db)
    return await service.check_authorization(request.action_type, request.requested_level)


@router.delete("/authorizations/{authorization_id}")
async def revoke_authorization(authorization_id: str, db=Depends(get_db_session)):
    """Owner revokes an authorization."""
    service = OwnerAuthService(db)
    ok = await service.revoke_authorization(authorization_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Authorization not found")
    return {"status": "revoked"}
