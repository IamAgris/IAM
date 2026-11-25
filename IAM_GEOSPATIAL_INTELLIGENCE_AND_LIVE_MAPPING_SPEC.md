# IAM — Geospatial Intelligence and Live Mapping Specification

**Document:** 16 (addendum to Documents 01–15)  
**Version:** 1.0 · 25 November 2026  
**Status:** FROZEN — requirements scope closed; provider/free-tier verification at implementation  
**Parent:** `IAM_MASTER_ARCHITECTURE.md`  
**Related:** `IAM_UNIVERSAL_WEBSITE_INTERACTION_SPEC.md`, `IAM_GLOBAL_RESEARCH_AND_KNOWLEDGE_SPEC.md`, `IAM_OWNER_DECISIONS.md`  
**Confirmed decision:** OD-32 (geospatial intelligence and live mapping)

---

## 1. Purpose

IAM must understand the world geographically, use maps for research/navigation, and display interactive live maps in its own interface — without depending on a single mapping provider.

---

## 2. Geospatial Intelligence Engine

Understand countries, continents, territories and borders; cities, suburbs and streets; buildings, addresses, landmarks and points of interest; roads, transport networks; natural features; administrative boundaries; population and public demographics; terrain, elevation and climate; infrastructure, ports, airports, rail and public facilities. Understand relationships, distances, directions, coordinates and spatial data.

---

## 3. Interactive and live maps

Capabilities: zoom, pan, rotation and layers; street/satellite/terrain where available; location/address/place search; markers, boundaries, routes and geographic overlays; distance, area and route calculation; provider comparison; traffic, weather, public transport and other live information where supported; dataset change tracking; maps inside IAM's own dashboard; maps used as part of reasoning and research; desktop and mobile layouts.

A map is not live simply because it is interactive: every live layer must show source and last-update time.

---

## 4. Multi-provider layer and free-tier discipline

Initial technologies to evaluate: **OpenStreetMap** (open geographic data), **MapLibre** (vector-tile rendering), **GeoServer** (geospatial services), **QGIS** (analysis/visualisation), **OpenFreeMap** (tile provider candidate). Also investigate MapTiler, HERE, TomTom, Google Maps and regional providers; NASA Earthdata, Copernicus, USGS, Natural Earth, Overture Maps; PostGIS, GDAL, OpenRouteService, OSRM.

Evaluate availability, licence, free quota, API restrictions, commercial terms and ARM64 compatibility. Open-source software does not imply unlimited free data or hosting. Never silently switch to paid usage; OEDIE governs discovery and replacement (OD-15).

---

## 5. Live geospatial information

Traffic (congestion, closures), weather, public transport, aviation, maritime, natural disasters, environment/air quality, satellite imagery and observation, public infrastructure. Preserve source and freshness indicators for all live data.

---

## 6. Location intelligence and privacy

Geocoding and reverse geocoding; geospatial search by distance/region/category/boundary; 3D and indoor mapping where public; historical map/border comparison; geospatial simulation; route optimisation; offline maps; IAM-owned permitted datasets; spatial analysis; geospatial collaboration between trusted nodes; map versioning; coordinate systems (GPS, lat/long, projections); data conversion (GeoJSON, KML, GPX, GeoPackage, vector tiles, raster).

Privacy: approximate location via permitted IP GeoIP; precise GPS only with explicit permission; no covert tracking of visitors or devices; no permanent location history without purpose and permission; no use of maps for stalking, targeting individuals or attacking sensitive infrastructure.

---

## 7. Consolidated modules

1. Geospatial Intelligence Engine
2. Global Geographic Knowledge Engine
3. Multi-Provider Mapping Integration Engine
4. Interactive and Live Map Engine
5. Location Discovery and Resolution Engine
6. Geographic Data Collection and Verification Engine
7. Routing and Navigation Intelligence Engine
8. Live Geospatial Information Engine
9. Satellite and Earth Observation Research Engine
10. Geographic Analysis and GIS Engine
11. Map Provider Discovery and Switching Engine
12. Geospatial Privacy and Permission Engine
13. Offline and Distributed Map Engine
14. Geospatial Security and Audit Engine

All are modules of the intelligence architecture, not fourteen standalone services.

---

## 8. Provider independence

IAM retains its own geographic knowledge and indexes independently of any provider. If a provider disappears, changes its API or starts charging, IAM switches providers without losing accumulated geographic knowledge.

---

## 9. Acceptance criteria

1. Interactive maps display in IAM's interface on desktop and mobile.
2. At least two providers can serve the same view; switching preserves IAM's own data.
3. Live layers show source and freshness.
4. Geocoding, routing, spatial analysis and format conversion work on public data.
5. Free quotas and licence conditions are recorded per provider; no silent paid usage.
6. Precise location requires explicit permission; no covert tracking.
7. Geographic knowledge survives provider loss and syncs only as approved to trusted nodes.
8. Maps are never used to facilitate harm against individuals or sensitive infrastructure.
