"""Website Account Lifecycle API routes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.web_account_service import (
    WebsiteAccountError,
    WebsiteAccountService,
)

router = APIRouter(prefix="/api/v1/web/accounts", tags=["web-accounts"])


class AccountCreate(BaseModel):
    website_knowledge_id: str
    account_type: str
    username: str
    owner_entity: str
    email: Optional[str] = None
    verification_status: str = "unverified"
    mfa_status: str = "none"
    recovery_method: Optional[str] = None
    is_owned_by_iam: bool = False
    is_owned_by_creator: bool = False
    is_authorised_access: bool = False


class AccountSecurityUpdate(BaseModel):
    mfa_status: Optional[str] = None
    recovery_method: Optional[str] = None
    passkey_registered: Optional[bool] = None


class AccountStatusUpdate(BaseModel):
    account_status: str
    suspension_reason: Optional[str] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _fail(exc: WebsiteAccountError) -> HTTPException:
    return HTTPException(400, str(exc))


@router.post("")
async def create_account(  # type: ignore[no-untyped-def]
    payload: AccountCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new website account lifecycle record."""
    try:
        return await WebsiteAccountService(db).create(
            website_knowledge_id=payload.website_knowledge_id,
            account_type=payload.account_type,
            username=payload.username,
            owner_entity=payload.owner_entity,
            email=payload.email,
            verification_status=payload.verification_status,
            mfa_status=payload.mfa_status,
            recovery_method=payload.recovery_method,
            is_owned_by_iam=payload.is_owned_by_iam,
            is_owned_by_creator=payload.is_owned_by_creator,
            is_authorised_access=payload.is_authorised_access,
            actor=_actor(request),
        )
    except WebsiteAccountError as exc:
        raise _fail(exc) from exc


@router.get("")
async def list_accounts(  # type: ignore[no-untyped-def]
    website_knowledge_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
):
    """List website account lifecycle records."""
    return await WebsiteAccountService(db).list(website_knowledge_id)


@router.get("/{account_id}")
async def get_account(account_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    """Get a single website account lifecycle record."""
    try:
        return await WebsiteAccountService(db).get(account_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.patch("/{account_id}/security")
async def update_security(  # type: ignore[no-untyped-def]
    account_id: str,
    payload: AccountSecurityUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Update security configuration for an account."""
    try:
        return await WebsiteAccountService(db).update_security(
            account_id,
            mfa_status=payload.mfa_status,
            recovery_method=payload.recovery_method,
            passkey_registered=payload.passkey_registered,
            actor=_actor(request),
        )
    except WebsiteAccountError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.patch("/{account_id}/status")
async def update_status(  # type: ignore[no-untyped-def]
    account_id: str,
    payload: AccountStatusUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Suspend, restrict, close or reactivate an account."""
    try:
        return await WebsiteAccountService(db).update_status(
            account_id,
            account_status=payload.account_status,
            suspension_reason=payload.suspension_reason,
            actor=_actor(request),
        )
    except WebsiteAccountError as exc:
        raise _fail(exc) from exc
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{account_id}/login")
async def record_login(  # type: ignore[no-untyped-def]
    account_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Record a successful login for an account."""
    try:
        return await WebsiteAccountService(db).record_login(
            account_id, actor=_actor(request)
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc