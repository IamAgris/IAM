"""Geospatial intelligence and live mapping routes (OD-32)."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.geo_service import GeoError, GeoService

router = APIRouter(prefix="/api/v1/geo", tags=["geospatial"])


class ProviderRequest(BaseModel):
    name: str
    kind: str
    base_url: str
    licence: str = "unknown"
    free_quota: Optional[str] = None
    requires_key: bool = False
    is_paid: bool = False
    paid_use_approved: bool = False
    terms_url: Optional[str] = None


class PlaceRequest(BaseModel):
    name: str
    latitude: float
    longitude: float
    place_type: str = "poi"
    country_code: Optional[str] = None
    metadata: Dict[str, Any] = {}
    source: str = "local"
    source_url: Optional[str] = None
    confidence: float = 0.8


class GeocodeRequest(BaseModel):
    query: str
    local_only: bool = True
    provider_id: Optional[str] = None


class GeoJSONRequest(BaseModel):
    name: str
    data: Dict[str, Any]
    licence: str
    source: str = "local"


class FeedRequest(BaseModel):
    name: str
    category: str
    source: str
    source_url: str
    refresh_seconds: int = 3600


class TileRequest(BaseModel):
    provider_id: str
    tile_key: str
    content: str


class PermissionRequest(BaseModel):
    subject: str
    precision: str
    purpose: str
    granted_by: str


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return str(credential.get("name", "sdk")) if credential else "sdk"


def _handle(exc: GeoError) -> HTTPException:
    return HTTPException(status_code=404 if "not found" in str(exc) else 400, detail=str(exc))


@router.post("/providers")
async def register_provider(payload: ProviderRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await GeoService(db).register_provider(payload.model_dump(), _actor(request))
    except GeoError as exc:
        raise _handle(exc)


@router.get("/providers")
async def providers(kind: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    return await GeoService(db).providers(kind)


@router.get("/map/config")
async def map_config(kind: str = "tile", db: AsyncSession = Depends(get_db_session)):
    return await GeoService(db).map_config(kind)


@router.post("/places")
async def add_place(payload: PlaceRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await GeoService(db).add_place(payload.model_dump(), _actor(request))
    except GeoError as exc:
        raise _handle(exc)


@router.get("/places")
async def places(query: str, country_code: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    return await GeoService(db).places(query, country_code)


@router.get("/places/nearby")
async def nearby(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_km: float = 25,
    db: AsyncSession = Depends(get_db_session),
):
    return await GeoService(db).nearby(latitude, longitude, radius_km)


@router.get("/places/reverse")
async def reverse(
    latitude: float = Query(...),
    longitude: float = Query(...),
    radius_km: float = 25,
    db: AsyncSession = Depends(get_db_session),
):
    return await GeoService(db).reverse(latitude, longitude, radius_km)


@router.post("/geocode")
async def geocode(payload: GeocodeRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        return await GeoService(db).geocode(payload.query, payload.local_only, payload.provider_id)
    except GeoError as exc:
        raise _handle(exc)


@router.post("/data")
async def import_geojson(payload: GeoJSONRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await GeoService(db).import_geojson(
            payload.data, payload.name, payload.licence, payload.source, _actor(request)
        )
    except GeoError as exc:
        raise _handle(exc)


@router.get("/data")
async def data_files(db: AsyncSession = Depends(get_db_session)):
    return await GeoService(db).data_files()


@router.get("/data/export")
async def export_geojson(place_ids: Optional[str] = None, db: AsyncSession = Depends(get_db_session)):
    ids = [item for item in (place_ids or "").split(",") if item]
    return await GeoService(db).export_geojson(ids or None)


@router.post("/feeds")
async def register_feed(payload: FeedRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        return await GeoService(db).register_feed(payload.model_dump())
    except GeoError as exc:
        raise _handle(exc)


@router.get("/feeds")
async def feeds(db: AsyncSession = Depends(get_db_session)):
    return await GeoService(db).feeds()


@router.post("/feeds/{feed_id}/snapshot")
async def feed_snapshot(feed_id: str, payload: Dict[str, Any], db: AsyncSession = Depends(get_db_session)):
    try:
        return await GeoService(db).snapshot_feed(feed_id, payload.get("data", payload))
    except GeoError as exc:
        raise _handle(exc)


@router.post("/tiles")
async def cache_tile(payload: TileRequest, db: AsyncSession = Depends(get_db_session)):
    try:
        return await GeoService(db).cache_tile(payload.provider_id, payload.tile_key, payload.content)
    except GeoError as exc:
        raise _handle(exc)


@router.get("/tiles/status")
async def tile_status(db: AsyncSession = Depends(get_db_session)):
    return await GeoService(db).tile_status()


@router.post("/permissions")
async def grant_permission(payload: PermissionRequest, request: Request, db: AsyncSession = Depends(get_db_session)):
    try:
        return await GeoService(db).grant_permission(
            payload.subject, payload.precision, payload.purpose, payload.granted_by, _actor(request)
        )
    except GeoError as exc:
        raise _handle(exc)


@router.get("/location")
async def resolve_location(
    subject: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    db: AsyncSession = Depends(get_db_session),
):
    return await GeoService(db).resolve_location(subject, latitude, longitude)


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db_session)):
    return await GeoService(db).status()
