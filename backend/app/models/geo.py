"""Geospatial knowledge, multi-provider maps and location privacy (OD-32).

IAM keeps its own geographic data and indexes so provider loss never removes
accumulated knowledge. Live data always carries source and freshness.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class GeoProvider(Base):
    __tablename__ = "geo_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    kind = Column(Text, nullable=False)  # tile, geocoder, routing, dataset, live_feed
    base_url = Column(Text, nullable=False)
    licence = Column(Text, nullable=False, default="unknown")
    free_quota = Column(Text, nullable=True)
    requires_key = Column(Boolean, nullable=False, default=False)
    is_paid = Column(Boolean, nullable=False, default=False)
    paid_use_approved = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    terms_url = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('tile', 'geocoder', 'routing', 'dataset', 'live_feed')",
            name="ck_geo_provider_kind",
        ),
    )


class GeoPlace(Base):
    __tablename__ = "geo_places"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, index=True)
    place_type = Column(Text, nullable=False, default="poi")
    country_code = Column(Text, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    attributes = Column(JSON, nullable=False, default=dict)
    source = Column(Text, nullable=False, default="local")
    source_url = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.8)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_geo_place_latitude"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_geo_place_longitude"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_geo_place_confidence"),
    )


class GeoDataFile(Base):
    __tablename__ = "geo_data_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    data_format = Column(Text, nullable=False, default="geojson")
    content_hash = Column(Text, nullable=False, index=True)
    data = Column(JSON, nullable=False, default=dict)
    licence = Column(Text, nullable=False, default="unknown")
    source = Column(Text, nullable=False, default="local")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LiveGeoFeed(Base):
    __tablename__ = "live_geo_feeds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False, unique=True)
    category = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    source_url = Column(Text, nullable=False)
    refresh_seconds = Column(Integer, nullable=False, default=3600)
    last_fetched_at = Column(DateTime(timezone=True), nullable=True)
    last_data_hash = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "category IN ('traffic', 'weather', 'transit', 'aviation', 'maritime', "
            "'disaster', 'environment', 'satellite', 'infrastructure')",
            name="ck_live_geo_feed_category",
        ),
    )


class MapTileCache(Base):
    __tablename__ = "map_tile_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(
        UUID(as_uuid=True),
        ForeignKey("geo_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    tile_key = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False)
    size_bytes = Column(Integer, nullable=False, default=0)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class LocationPermission(Base):
    __tablename__ = "location_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject = Column(Text, nullable=False, index=True)
    precision = Column(Text, nullable=False)  # approximate | precise
    purpose = Column(Text, nullable=False)
    granted_by = Column(Text, nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "precision IN ('approximate', 'precise')",
            name="ck_location_permission_precision",
        ),
    )
