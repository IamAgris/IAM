"""Geospatial knowledge, multi-provider maps and location privacy (OD-32).

IAM owns its place index and datasets. Providers are replaceable adapters; a
map is never assumed live just because it is interactive — freshness is
measured from the source's own last successful observation.
"""

import base64
import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.geo import (
    GeoDataFile,
    GeoPlace,
    GeoProvider,
    LiveGeoFeed,
    LocationPermission,
    MapTileCache,
)
from app.models.security import AuditEvent

PROVIDER_KINDS = {"tile", "geocoder", "routing", "dataset", "live_feed"}
FEED_CATEGORIES = {
    "traffic", "weather", "transit", "aviation", "maritime",
    "disaster", "environment", "satellite", "infrastructure",
}


class GeoError(ValueError):
    pass


def _hash(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


class GeoService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ---------------------------------------------------------------- providers

    async def register_provider(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        for field in ("name", "kind", "base_url"):
            if not payload.get(field):
                raise GeoError(f"{field} is required")
        if payload["kind"] not in PROVIDER_KINDS:
            raise GeoError("invalid provider kind")
        if payload.get("is_paid") and not payload.get("paid_use_approved"):
            raise GeoError(
                "paid provider requires explicit approval; IAM must not silently switch to paid usage"
            )
        existing = await self.db.execute(
            select(GeoProvider).where(GeoProvider.name == payload["name"])
        )
        if existing.scalar_one_or_none():
            raise GeoError("provider already registered")
        provider = GeoProvider(
            name=payload["name"],
            kind=payload["kind"],
            base_url=payload["base_url"],
            licence=payload.get("licence", "unknown"),
            free_quota=payload.get("free_quota"),
            requires_key=bool(payload.get("requires_key", False)),
            is_paid=bool(payload.get("is_paid", False)),
            paid_use_approved=bool(payload.get("paid_use_approved", False)),
            verified_at=payload.get("verified_at"),
            terms_url=payload.get("terms_url"),
        )
        self.db.add(provider)
        self.db.add(
            AuditEvent(
                event_type="geo_provider_registered",
                actor=actor,
                target=provider.name,
                details={"kind": provider.kind, "paid": provider.is_paid},
            )
        )
        await self.db.commit()
        await self.db.refresh(provider)
        return self.provider_dict(provider)

    async def providers(self, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        query = select(GeoProvider)
        if kind:
            query = query.where(GeoProvider.kind == kind)
        result = await self.db.execute(query.order_by(GeoProvider.name))
        return [self.provider_dict(p) for p in result.scalars().all()]

    async def map_config(self, kind: str = "tile") -> Dict[str, Any]:
        providers = await self.providers(kind)
        usable = [p for p in providers if p["is_active"] and not p["is_paid"]]
        return {
            "kind": kind,
            "providers": usable,
            "attribution_required": True,
            "note": "Free providers only; paid providers never enabled implicitly.",
            "own_place_index_available": True,
        }

    # -------------------------------------------------------------------- places

    async def add_place(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        for field in ("name", "latitude", "longitude"):
            if payload.get(field) is None:
                raise GeoError(f"{field} is required")
        lat, lon = float(payload["latitude"]), float(payload["longitude"])
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise GeoError("latitude/longitude outside valid range")
        place = GeoPlace(
            name=payload["name"],
            place_type=payload.get("place_type", "poi"),
            country_code=payload.get("country_code"),
            latitude=lat,
            longitude=lon,
            attributes=payload.get("metadata") or {},
            source=payload.get("source", "local"),
            source_url=payload.get("source_url"),
            confidence=float(payload.get("confidence", 0.8)),
        )
        self.db.add(place)
        await self.db.commit()
        await self.db.refresh(place)
        return self.place_dict(place)

    async def all_places(self, limit: int = 200) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(GeoPlace).limit(min(limit, 500)))
        return [self.place_dict(p) for p in result.scalars().all()]

    async def places(self, query: str, country_code: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        statement = select(GeoPlace).where(GeoPlace.name.ilike(f"%{query}%"))
        if country_code:
            statement = statement.where(GeoPlace.country_code == country_code)
        result = await self.db.execute(statement.limit(min(limit, 200)))
        return [self.place_dict(p) for p in result.scalars().all()]

    async def nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 25,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(GeoPlace))
        matches = []
        for place in result.scalars().all():
            distance = haversine_km(latitude, longitude, place.latitude, place.longitude)
            if distance <= radius_km:
                item = self.place_dict(place)
                item["distance_km"] = round(distance, 3)
                matches.append(item)
        matches.sort(key=lambda p: p["distance_km"])
        return matches[: min(limit, 200)]

    async def reverse(self, latitude: float, longitude: float, radius_km: float = 25) -> Dict[str, Any]:
        candidates = await self.nearby(latitude, longitude, radius_km, 1)
        return {
            "query": {"latitude": latitude, "longitude": longitude},
            "nearest": candidates[0] if candidates else None,
            "confidence": candidates[0]["confidence"] if candidates else 0.0,
        }

    async def geocode(
        self,
        query: str,
        local_only: bool = True,
        provider_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        local = await self.places(query)
        if local_only or not provider_id:
            return {"source": "own_place_index", "results": local, "provider_independent": True}
        result = await self.db.execute(
            select(GeoProvider).where(GeoProvider.id == provider_id, GeoProvider.kind == "geocoder")
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise GeoError("geocoder provider not found")
        try:
            async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "IAM-Geospatial/1.0"}) as client:
                response = await client.get(
                    provider.base_url,
                    params={"q": query, "format": "json", "limit": 5},
                )
            if response.status_code != 200:
                raise GeoError(f"geocoder returned {response.status_code}")
            items = response.json()
            results = [
                {
                    "name": item.get("display_name", query),
                    "latitude": float(item.get("lat", 0)),
                    "longitude": float(item.get("lon", 0)),
                    "source": provider.name,
                }
                for item in items
                if item.get("lat") and item.get("lon")
            ]
            return {"source": provider.name, "results": results, "licence": provider.licence}
        except httpx.HTTPError as exc:
            raise GeoError(f"geocoder unavailable: {exc}") from exc

    # ------------------------------------------------------------------ GIS data

    async def import_geojson(
        self,
        data: Dict[str, Any],
        name: str,
        licence: str,
        source: str,
        actor: str = "sdk",
    ) -> Dict[str, Any]:
        if data.get("type") != "FeatureCollection" or not isinstance(data.get("features"), list):
            raise GeoError("expected a GeoJSON FeatureCollection")
        imported = 0
        for feature in data["features"]:
            geometry = feature.get("geometry") or {}
            if geometry.get("type") != "Point":
                continue
            coords = geometry.get("coordinates") or []
            if len(coords) < 2:
                continue
            props = feature.get("properties") or {}
            await self.add_place(
                {
                    "name": props.get("name") or "unnamed point",
                    "place_type": props.get("place_type", "poi"),
                    "country_code": props.get("country_code"),
                    "latitude": coords[1],
                    "longitude": coords[0],
                    "metadata": props,
                    "source": source,
                    "confidence": props.get("confidence", 0.7),
                },
                actor,
            )
            imported += 1
        record = GeoDataFile(
            name=name,
            data_format="geojson",
            content_hash=_hash(data),
            data=data,
            licence=licence,
            source=source,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return {
            "id": str(record.id),
            "imported_places": imported,
            "content_hash": record.content_hash,
            "licence": licence,
        }

    async def export_geojson(self, place_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        if place_ids:
            result = await self.db.execute(
                select(GeoPlace).where(GeoPlace.id.in_(place_ids))
            )
        else:
            result = await self.db.execute(select(GeoPlace))
        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [place.longitude, place.latitude],
                },
                "properties": {
                    "name": place.name,
                    "place_type": place.place_type,
                    "country_code": place.country_code,
                    "confidence": place.confidence,
                    **(place.attributes or {}),
                },
            }
            for place in result.scalars().all()
        ]
        return {"type": "FeatureCollection", "features": features}

    async def data_files(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(GeoDataFile).order_by(GeoDataFile.created_at.desc()))
        return [
            {
                "id": str(f.id),
                "name": f.name,
                "format": f.data_format,
                "content_hash": f.content_hash,
                "licence": f.licence,
                "source": f.source,
            }
            for f in result.scalars().all()
        ]

    # -------------------------------------------------------------- live feeds

    async def register_feed(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        for field in ("name", "category", "source", "source_url"):
            if not payload.get(field):
                raise GeoError(f"{field} is required")
        if payload["category"] not in FEED_CATEGORIES:
            raise GeoError("invalid live feed category")
        existing = await self.db.execute(
            select(LiveGeoFeed).where(LiveGeoFeed.name == payload["name"])
        )
        if existing.scalar_one_or_none():
            raise GeoError("feed already registered")
        feed = LiveGeoFeed(
            name=payload["name"],
            category=payload["category"],
            source=payload["source"],
            source_url=payload["source_url"],
            refresh_seconds=int(payload.get("refresh_seconds", 3600)),
        )
        self.db.add(feed)
        await self.db.commit()
        await self.db.refresh(feed)
        return self.feed_dict(feed)

    async def snapshot_feed(self, feed_id: str, data: Any) -> Dict[str, Any]:
        result = await self.db.execute(select(LiveGeoFeed).where(LiveGeoFeed.id == feed_id))
        feed = result.scalar_one_or_none()
        if not feed:
            raise GeoError("feed not found")
        digest = _hash(data)
        changed = feed.last_data_hash is not None and feed.last_data_hash != digest
        feed.last_data_hash = digest
        feed.last_fetched_at = datetime.now(timezone.utc)
        await self.db.commit()
        return {
            "feed_id": feed_id,
            "changed": changed,
            "source": feed.source,
            "source_url": feed.source_url,
            **self.freshness(feed),
        }

    async def feeds(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(LiveGeoFeed).order_by(LiveGeoFeed.name))
        return [self.feed_dict(feed) for feed in result.scalars().all()]

    @staticmethod
    def freshness(feed: LiveGeoFeed) -> Dict[str, Any]:
        if not feed.last_fetched_at:
            return {"freshness": "never_observed", "is_live": False}
        age = (datetime.now(timezone.utc) - feed.last_fetched_at).total_seconds()
        return {
            "last_fetched_at": feed.last_fetched_at.isoformat(),
            "age_seconds": round(age, 1),
            "freshness": "current" if age <= feed.refresh_seconds else "stale",
            "is_live": age <= feed.refresh_seconds,
        }

    # -------------------------------------------------------------- tile cache

    async def cache_tile(self, provider_id: str, tile_key: str, content: str) -> Dict[str, Any]:
        result = await self.db.execute(
            select(GeoProvider).where(GeoProvider.id == provider_id, GeoProvider.is_active.is_(True))
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise GeoError("tile provider not found or inactive")
        try:
            raw = base64.b64decode(content, validate=True)
        except Exception as exc:
            raise GeoError("tile content must be base64 encoded") from exc
        entry = MapTileCache(
            provider_id=provider.id,
            tile_key=tile_key,
            content_hash=hashlib.sha256(raw).hexdigest(),
            size_bytes=len(raw),
        )
        self.db.add(entry)
        await self.db.commit()
        return {"tile_key": tile_key, "size_bytes": len(raw), "offline_available": True}

    async def tile_status(self) -> Dict[str, Any]:
        result = await self.db.execute(select(MapTileCache))
        entries = result.scalars().all()
        return {
            "cached_tiles": len(entries),
            "total_bytes": sum(e.size_bytes for e in entries),
            "offline_maps_available": bool(entries),
        }

    # ----------------------------------------------------------- location rules

    async def grant_permission(
        self,
        subject: str,
        precision: str,
        purpose: str,
        granted_by: str,
        actor: str = "sdk",
    ) -> Dict[str, Any]:
        if precision not in {"approximate", "precise"}:
            raise GeoError("precision must be approximate or precise")
        if not purpose:
            raise GeoError("a location purpose is required")
        if precision == "precise" and (not granted_by or granted_by == subject):
            raise GeoError("precise location requires explicit permission from a human/owner")
        permission = LocationPermission(
            subject=subject,
            precision=precision,
            purpose=purpose,
            granted_by=granted_by,
        )
        self.db.add(permission)
        self.db.add(
            AuditEvent(
                event_type="location_permission_granted",
                actor=actor,
                target=subject,
                details={"precision": precision, "purpose": purpose, "granted_by": granted_by},
            )
        )
        await self.db.commit()
        await self.db.refresh(permission)
        return {
            "id": str(permission.id),
            "subject": subject,
            "precision": precision,
            "purpose": purpose,
        }

    async def resolve_location(
        self,
        subject: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict[str, Any]:
        result = await self.db.execute(
            select(LocationPermission)
            .where(
                LocationPermission.subject == subject,
                LocationPermission.revoked_at.is_(None),
            )
            .order_by(LocationPermission.granted_at.desc())
        )
        permissions = result.scalars().all()
        if not permissions:
            return {"permitted": False, "reason": "no active location permission"}
        precision = permissions[0].precision
        if precision == "precise":
            if latitude is None or longitude is None:
                return {"permitted": False, "reason": "precise permission requires supplied coordinates"}
            return {
                "permitted": True,
                "precision": "precise",
                "latitude": latitude,
                "longitude": longitude,
                "purpose": permissions[0].purpose,
            }
        return {
            "permitted": True,
            "precision": "approximate",
            "method": "permitted_ip_geoip_estimate",
            "purpose": permissions[0].purpose,
            "note": "estimate only; never treated as exact location",
        }

    async def status(self) -> Dict[str, Any]:
        providers = await self.providers()
        places = await self.db.execute(select(GeoPlace))
        feeds = await self.feeds()
        return {
            "providers": len(providers),
            "places": len(places.scalars().all()),
            "live_feeds": len(feeds),
            "provider_independent_knowledge": True,
            "claim": "freshness_measured_not_assumed",
        }

    @staticmethod
    def provider_dict(provider: GeoProvider) -> Dict[str, Any]:
        return {
            "id": str(provider.id),
            "name": provider.name,
            "kind": provider.kind,
            "base_url": provider.base_url,
            "licence": provider.licence,
            "free_quota": provider.free_quota,
            "requires_key": provider.requires_key,
            "is_paid": provider.is_paid,
            "is_active": provider.is_active,
            "terms_url": provider.terms_url,
        }

    @staticmethod
    def render_svg(
        places: List[Dict[str, Any]], width: int = 800, height: int = 400
    ) -> str:
        """Render a provider-neutral SVG map fragment from place records.

        This is backend rendering support only — no frontend page, no external
        tile provider and no executable JavaScript. Coordinates use a simple
        equirectangular projection; untrusted labels are XML-escaped.
        """
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            'role="img" aria-label="IAM geospatial overview">',
            '<rect width="100%" height="100%" fill="#0B0F26"/>',
        ]
        for fraction in (0.25, 0.5, 0.75):
            y = int(height * fraction)
            x = int(width * fraction)
            lines.append(
                f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="#2A3260" '
                'stroke-width="1"/>'
            )
            lines.append(
                f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="#2A3260" '
                'stroke-width="1"/>'
            )
        for place in places[:200]:
            raw_lat = place.get("latitude")
            raw_lon = place.get("longitude")
            if raw_lat is None or raw_lon is None:
                continue
            try:
                lat = float(raw_lat)
                lon = float(raw_lon)
            except (TypeError, ValueError):
                continue
            px = (lon + 180) / 360 * width
            py = (90 - lat) / 180 * height
            label = escape(str(place.get("name") or "place")[:80])
            lines.append(
                f'<circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="#8FA6FF"/>'
            )
            lines.append(
                f'<text x="{px + 8:.1f}" y="{py - 8:.1f}" fill="#E9EDFF" '
                f'font-size="12">{label}</text>'
            )
        lines.append("</svg>")
        return "\n".join(lines)

    @staticmethod
    def place_dict(place: GeoPlace) -> Dict[str, Any]:
        return {
            "id": str(place.id),
            "name": place.name,
            "place_type": place.place_type,
            "country_code": place.country_code,
            "latitude": place.latitude,
            "longitude": place.longitude,
            "metadata": place.attributes,
            "source": place.source,
            "confidence": place.confidence,
        }

    @staticmethod
    def feed_dict(feed: LiveGeoFeed) -> Dict[str, Any]:
        return {
            "id": str(feed.id),
            "name": feed.name,
            "category": feed.category,
            "source": feed.source,
            "source_url": feed.source_url,
            "refresh_seconds": feed.refresh_seconds,
            "is_active": feed.is_active,
            **GeoService.freshness(feed),
        }
