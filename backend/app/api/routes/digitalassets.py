"""Digital asset registry API — owner-owned assets, licences, IP and domains."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.digitalassets_service import (
    DigitalAssetError,
    DigitalAssetsService,
)

router = APIRouter(prefix="/api/v1", tags=["digital-assets"])


class AssetCreate(BaseModel):
    name: str
    asset_type: str
    owner_entity: str
    description: Optional[str] = None
    source_code_location: Optional[str] = None
    licence_type: Optional[str] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source_code_location: Optional[str] = None
    licence_type: Optional[str] = None


class LicenceCreate(BaseModel):
    licence_text: Optional[str] = None
    licence_url: Optional[str] = None
    granted_to: Optional[str] = None


class IPCreate(BaseModel):
    ip_type: str
    registration_number: Optional[str] = None
    owner_entity: str


class DomainCreate(BaseModel):
    domain_name: str
    registrar: Optional[str] = None
    expires_at: Optional[str] = None
    owner_entity: str


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "iam") if credential else "iam"


def _deny(exc: DigitalAssetError) -> HTTPException:
    return HTTPException(403, str(exc))


@router.get("/digital-assets")
async def list_assets(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await DigitalAssetsService(db).list()


@router.post("/digital-assets")
async def create_asset(  # type: ignore[no-untyped-def]
    payload: AssetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await DigitalAssetsService(db).create(
            name=payload.name,
            asset_type=payload.asset_type,
            owner_entity=payload.owner_entity,
            description=payload.description,
            source_code_location=payload.source_code_location,
            licence_type=payload.licence_type,
            actor=_actor(request),
        )
    except DigitalAssetError as exc:
        raise _deny(exc) from exc


@router.get("/digital-assets/{asset_id}")
async def get_asset(asset_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    try:
        return await DigitalAssetsService(db).get(asset_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.patch("/digital-assets/{asset_id}")
async def update_asset(  # type: ignore[no-untyped-def]
    asset_id: str,
    payload: AssetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await DigitalAssetsService(db).update(
            asset_id, payload.model_dump(exclude_none=True), _actor(request)
        )
    except DigitalAssetError as exc:
        raise _deny(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/digital-assets/{asset_id}")
async def delete_asset(  # type: ignore[no-untyped-def]
    asset_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await DigitalAssetsService(db).delete(asset_id, _actor(request))
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/digital-assets/{asset_id}/licences")
async def list_licences(asset_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    try:
        return await DigitalAssetsService(db).licences(asset_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/digital-assets/{asset_id}/licences")
async def add_licence(  # type: ignore[no-untyped-def]
    asset_id: str,
    payload: LicenceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await DigitalAssetsService(db).add_licence(
            asset_id,
            licence_text=payload.licence_text,
            licence_url=payload.licence_url,
            granted_to=payload.granted_to,
            actor=_actor(request),
        )
    except DigitalAssetError as exc:
        raise _deny(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/digital-assets/{asset_id}/ip")
async def list_ip(asset_id: str, db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    try:
        return await DigitalAssetsService(db).ip_records(asset_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/digital-assets/{asset_id}/ip")
async def add_ip(  # type: ignore[no-untyped-def]
    asset_id: str,
    payload: IPCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await DigitalAssetsService(db).add_ip(
            asset_id,
            ip_type=payload.ip_type,
            registration_number=payload.registration_number,
            owner_entity=payload.owner_entity,
            actor=_actor(request),
        )
    except DigitalAssetError as exc:
        raise _deny(exc) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/domain-registrations")
async def list_domains(db: AsyncSession = Depends(get_db_session)):  # type: ignore[no-untyped-def]
    return await DigitalAssetsService(db).domains()


@router.post("/domain-registrations")
async def register_domain(  # type: ignore[no-untyped-def]
    payload: DomainCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await DigitalAssetsService(db).register_domain(
            domain_name=payload.domain_name,
            registrar=payload.registrar,
            expires_at=payload.expires_at,
            owner_entity=payload.owner_entity,
            actor=_actor(request),
        )
    except DigitalAssetError as exc:
        raise _deny(exc) from exc
    except ValueError as exc:
        raise HTTPException(400, "expires_at must be an ISO-8601 date") from exc
