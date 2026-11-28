"""Encrypted website credential vault endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.website_credentials import (
    CredentialError,
    WebsiteCredentialService,
    generate_password,
)

router = APIRouter(prefix="/api/v1/credentials/websites", tags=["website-credentials"])


class CredentialRegister(BaseModel):
    site: str
    url: str
    username: str
    owner_entity: str
    password: Optional[str] = None
    secret_env_var: Optional[str] = None
    generate: bool = False


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


@router.get("/generate")
async def generate():  # type: ignore[no-untyped-def]
    """Return a fresh password once; IAM stores only its encrypted form."""
    return {"password": generate_password()}


@router.post("")
async def register(  # type: ignore[no-untyped-def]
    payload: CredentialRegister,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    password = payload.password
    if payload.generate and not password:
        password = generate_password()
    try:
        return await WebsiteCredentialService(db).register(
            site=payload.site,
            url=payload.url,
            username=payload.username,
            owner_entity=payload.owner_entity,
            password=password,
            secret_env_var=payload.secret_env_var,
            actor=_actor(request),
        )
    except CredentialError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("")
async def list_credentials(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await WebsiteCredentialService(db).list()


@router.post("/{credential_id}/reveal")
async def reveal(  # type: ignore[no-untyped-def]
    credential_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WebsiteCredentialService(db).reveal(credential_id, _actor(request))
    except CredentialError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{credential_id}/rotate")
async def rotate(  # type: ignore[no-untyped-def]
    credential_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WebsiteCredentialService(db).rotate(credential_id, _actor(request))
    except CredentialError as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{credential_id}/revoke")
async def revoke(  # type: ignore[no-untyped-def]
    credential_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await WebsiteCredentialService(db).revoke(credential_id, _actor(request))
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
