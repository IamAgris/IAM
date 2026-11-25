"""Owner authorization routes — human-controlled authority grants."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

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
    service = OwnerAuthService(db)
    return await service.grant_authorization(
        request.action_type, request.max_authority_level, request.spending_limit_usd,
        request.can_create_accounts, request.can_publish_externally,
        request.can_modify_own_security, request.scope, request.granted_by, request.expires_at,
    )


@router.get("/authorizations")
async def list_authorizations(db=Depends(get_db_session)):
    return await OwnerAuthService(db).list_authorizations()


@router.post("/authorizations/check")
async def check(request: CheckRequest, db=Depends(get_db_session)):
    return await OwnerAuthService(db).check_authorization(request.action_type, request.requested_level)


@router.delete("/authorizations/{authorization_id}")
async def revoke(authorization_id: str, db=Depends(get_db_session)):
    if not await OwnerAuthService(db).revoke_authorization(authorization_id):
        raise HTTPException(404, "Authorization not found")
    return {"status": "revoked"}
