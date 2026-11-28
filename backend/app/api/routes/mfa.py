"""WebAuthn passkey and TOTP MFA endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.mfa import MFAError, MFAService

router = APIRouter(prefix="/api/v1/mfa", tags=["mfa"])


class RegisterBegin(BaseModel):
    website_credential_id: str
    rp_id: str


class RegisterComplete(BaseModel):
    challenge_id: str
    credential_id: str
    public_key_pem: str


class AuthBegin(BaseModel):
    passkey_id: str


class VerifyAssertion(BaseModel):
    challenge_id: str
    credential_id: str
    authenticator_data: str
    client_data_json: str
    signature: str


class TotpEnroll(BaseModel):
    website_credential_id: str
    issuer: str = "IAM"
    account: str = "iam"


class TotpVerify(BaseModel):
    website_credential_id: str
    code: str


class CredentialRef(BaseModel):
    website_credential_id: str


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _fail(exc: MFAError) -> HTTPException:
    return HTTPException(403, str(exc))


@router.post("/passkeys/register/begin")
async def begin_registration(  # type: ignore[no-untyped-def]
    payload: RegisterBegin,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await MFAService(db).begin_registration(
            payload.website_credential_id, payload.rp_id, _actor(request)
        )
    except MFAError as exc:
        raise _fail(exc) from exc


@router.post("/passkeys/register/complete")
async def complete_registration(  # type: ignore[no-untyped-def]
    payload: RegisterComplete,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await MFAService(db).complete_registration(
            payload.challenge_id,
            payload.credential_id,
            payload.public_key_pem,
            _actor(request),
        )
    except MFAError as exc:
        raise _fail(exc) from exc


@router.post("/passkeys/authenticate/begin")
async def begin_authentication(  # type: ignore[no-untyped-def]
    payload: AuthBegin,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await MFAService(db).begin_authentication(payload.passkey_id, _actor(request))
    except MFAError as exc:
        raise _fail(exc) from exc


@router.post("/passkeys/authenticate/verify")
async def verify_assertion(  # type: ignore[no-untyped-def]
    payload: VerifyAssertion,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await MFAService(db).verify_assertion(
            payload.challenge_id,
            payload.credential_id,
            payload.authenticator_data,
            payload.client_data_json,
            payload.signature,
            _actor(request),
        )
    except MFAError as exc:
        raise _fail(exc) from exc


@router.get("/passkeys/{website_credential_id}")
async def list_passkeys(  # type: ignore[no-untyped-def]
    website_credential_id: str, db: AsyncSession = Depends(get_db_session)
):
    try:
        return await MFAService(db).passkeys(website_credential_id)
    except MFAError as exc:
        raise _fail(exc) from exc


@router.post("/totp/enroll")
async def enroll_totp(  # type: ignore[no-untyped-def]
    payload: TotpEnroll,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await MFAService(db).enroll_totp(
            payload.website_credential_id,
            payload.issuer,
            payload.account,
            _actor(request),
        )
    except MFAError as exc:
        raise _fail(exc) from exc


@router.post("/totp/verify")
async def verify_totp(  # type: ignore[no-untyped-def]
    payload: TotpVerify,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await MFAService(db).verify_totp(
            payload.website_credential_id, payload.code, _actor(request)
        )
    except MFAError as exc:
        raise _fail(exc) from exc


@router.post("/totp/disable")
async def disable_totp(  # type: ignore[no-untyped-def]
    payload: CredentialRef,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await MFAService(db).disable_totp(
            payload.website_credential_id, _actor(request)
        )
    except MFAError as exc:
        raise _fail(exc) from exc
