-- Geospatial intelligence, live maps and location privacy (OD-32)

CREATE TABLE IF NOT EXISTS geo_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL,
    base_url TEXT NOT NULL,
    licence TEXT NOT NULL DEFAULT 'unknown',
    free_quota TEXT,
    requires_key BOOLEAN NOT NULL DEFAULT FALSE,
    is_paid BOOLEAN NOT NULL DEFAULT FALSE,
    paid_use_approved BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    terms_url TEXT,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_geo_provider_kind CHECK (kind IN ('tile', 'geocoder', 'routing', 'dataset', 'live_feed'))
);

CREATE TABLE IF NOT EXISTS geo_places (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    place_type TEXT NOT NULL DEFAULT 'poi',
    country_code TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    source TEXT NOT NULL DEFAULT 'local',
    source_url TEXT,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.8,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_geo_place_latitude CHECK (latitude BETWEEN -90 AND 90),
    CONSTRAINT ck_geo_place_longitude CHECK (longitude BETWEEN -180 AND 180),
    CONSTRAINT ck_geo_place_confidence CHECK (confidence BETWEEN 0 AND 1)
);
CREATE INDEX IF NOT EXISTS ix_geo_places_name ON geo_places (name);
CREATE INDEX IF NOT EXISTS ix_geo_places_coords ON geo_places (latitude, longitude);

CREATE TABLE IF NOT EXISTS geo_data_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    data_format TEXT NOT NULL DEFAULT 'geojson',
    content_hash TEXT NOT NULL,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    licence TEXT NOT NULL DEFAULT 'unknown',
    source TEXT NOT NULL DEFAULT 'local',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_geo_data_files_hash ON geo_data_files (content_hash);

CREATE TABLE IF NOT EXISTS live_geo_feeds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT NOT NULL,
    refresh_seconds INTEGER NOT NULL DEFAULT 3600,
    last_fetched_at TIMESTAMPTZ,
    last_data_hash TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_live_geo_feed_category CHECK (
        category IN ('traffic', 'weather', 'transit', 'aviation', 'maritime',
                     'disaster', 'environment', 'satellite', 'infrastructure')
    )
);

CREATE TABLE IF NOT EXISTS map_tile_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID NOT NULL REFERENCES geo_providers(id) ON DELETE CASCADE,
    tile_key TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS location_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject TEXT NOT NULL,
    precision TEXT NOT NULL,
    purpose TEXT NOT NULL,
    granted_by TEXT NOT NULL,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ,
    CONSTRAINT ck_location_permission_precision CHECK (precision IN ('approximate', 'precise'))
);
CREATE INDEX IF NOT EXISTS ix_location_permissions_subject ON location_permissions (subject);
