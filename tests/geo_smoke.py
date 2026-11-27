"""Geospatial intelligence and live mapping smoke test (OD-32)."""

import base64
import os
import uuid

import httpx

from auth_headers import install_auth_headers

install_auth_headers()

BASE = "http://localhost:8000"
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main():
    if not os.environ.get("IAM_API_KEY"):
        print("SKIP: set IAM_API_KEY")
        return
    h = {"Authorization": f"Bearer {os.environ['IAM_API_KEY']}"}
    suffix = uuid.uuid4().hex[:8]

    free = httpx.post(
        f"{BASE}/api/v1/geo/providers",
        headers=h,
        json={
            "name": f"openstreetmap-{suffix}",
            "kind": "tile",
            "base_url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
            "licence": "ODbL",
            "free_quota": "fair use",
        },
        timeout=20,
    )
    provider_id = free.json().get("id")
    check("free tile provider registered", free.status_code == 200 and bool(provider_id), str(free.status_code))

    paid = httpx.post(
        f"{BASE}/api/v1/geo/providers",
        headers=h,
        json={
            "name": f"paid-provider-{suffix}",
            "kind": "tile",
            "base_url": "https://example.invalid/{z}/{x}/{y}.png",
            "is_paid": True,
        },
        timeout=20,
    )
    check("silent paid usage rejected", paid.status_code == 400, str(paid.status_code))

    cfg = httpx.get(f"{BASE}/api/v1/geo/map/config", headers=h, timeout=20)
    names = [p["name"] for p in cfg.json().get("providers", [])]
    check("map config uses free providers only", cfg.status_code == 200 and f"openstreetmap-{suffix}" in names, str(names))

    ct = httpx.post(
        f"{BASE}/api/v1/geo/places",
        headers=h,
        json={
            "name": f"Cape Town {suffix}",
            "latitude": -33.9249,
            "longitude": 18.4241,
            "place_type": "city",
            "country_code": "ZA",
        },
        timeout=20,
    )
    check("place stored in own index", ct.status_code == 200, str(ct.status_code))

    httpx.post(
        f"{BASE}/api/v1/geo/places",
        headers=h,
        json={
            "name": f"Johannesburg {suffix}",
            "latitude": -26.2041,
            "longitude": 28.0473,
            "place_type": "city",
            "country_code": "ZA",
        },
        timeout=20,
    )

    q = httpx.get(f"{BASE}/api/v1/geo/places", headers=h, params={"query": f"Cape Town {suffix}"}, timeout=20)
    check("place search", q.status_code == 200 and q.json()[0]["country_code"] == "ZA", str(q.json()))

    near = httpx.get(
        f"{BASE}/api/v1/geo/places/nearby",
        headers=h,
        params={"latitude": -33.9249, "longitude": 18.4241, "radius_km": 5},
        timeout=20,
    )
    check(
        "nearby uses geographic distance",
        near.status_code == 200 and all("distance_km" in p for p in near.json()),
        str(len(near.json())),
    )

    rev = httpx.get(
        f"{BASE}/api/v1/geo/places/reverse",
        headers=h,
        params={"latitude": -33.9249, "longitude": 18.4241, "radius_km": 5},
        timeout=20,
    )
    check("reverse geocoding from own index", rev.status_code == 200 and bool(rev.json().get("nearest")), str(rev.json().get("confidence")))

    geo = httpx.post(
        f"{BASE}/api/v1/geo/geocode",
        headers=h,
        json={"query": f"Cape Town {suffix}", "local_only": True},
        timeout=20,
    )
    check("provider-independent geocoding", geo.status_code == 200 and geo.json().get("provider_independent") is True, str(geo.status_code))

    gj = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [18.4111, -33.9567]},
                "properties": {"name": f"Table Mountain {suffix}", "place_type": "landmark"},
            }
        ],
    }
    imp = httpx.post(
        f"{BASE}/api/v1/geo/data",
        headers=h,
        json={"name": f"landmarks-{suffix}", "data": gj, "licence": "ODbL", "source": "openstreetmap"},
        timeout=20,
    )
    check("GeoJSON import", imp.status_code == 200 and imp.json().get("imported_places") == 1, str(imp.status_code))

    exp = httpx.get(f"{BASE}/api/v1/geo/data/export", headers=h, timeout=20)
    check("GeoJSON export", exp.status_code == 200 and exp.json().get("type") == "FeatureCollection", str(exp.status_code))

    feed = httpx.post(
        f"{BASE}/api/v1/geo/feeds",
        headers=h,
        json={
            "name": f"weather-{suffix}",
            "category": "weather",
            "source": "public weather service",
            "source_url": "https://example.invalid/weather",
            "refresh_seconds": 600,
        },
        timeout=20,
    )
    feed_id = feed.json().get("id")
    httpx.post(f"{BASE}/api/v1/geo/feeds/{feed_id}/snapshot", headers=h, json={"data": {"temp": 20}}, timeout=20)
    snap = httpx.post(
        f"{BASE}/api/v1/geo/feeds/{feed_id}/snapshot",
        headers=h,
        json={"data": {"temp": 24}},
        timeout=20,
    )
    check(
        "live feed shows source and freshness",
        snap.status_code == 200
        and snap.json().get("changed") is True
        and snap.json().get("is_live") is True
        and bool(snap.json().get("source")),
        str(snap.json()),
    )

    tile = httpx.post(
        f"{BASE}/api/v1/geo/tiles",
        headers=h,
        json={
            "provider_id": provider_id,
            "tile_key": "12/2048/1367",
            "content": base64.b64encode(b"tile-bytes").decode(),
        },
        timeout=20,
    )
    ts = httpx.get(f"{BASE}/api/v1/geo/tiles/status", headers=h, timeout=20)
    check("offline tile cache", tile.status_code == 200 and ts.json().get("offline_maps_available") is True, str(ts.json()))

    subject = f"visitor-{suffix}"
    granted = httpx.post(
        f"{BASE}/api/v1/geo/permissions",
        headers=h,
        json={
            "subject": subject,
            "precision": "approximate",
            "purpose": "regional content",
            "granted_by": "geoip_policy",
        },
        timeout=20,
    )
    loc = httpx.get(f"{BASE}/api/v1/geo/location", headers=h, params={"subject": subject}, timeout=20)
    check(
        "approximate location is an estimate",
        granted.status_code == 200
        and loc.json().get("precision") == "approximate"
        and "estimate" in loc.json().get("note", ""),
        str(loc.json()),
    )

    precise_subject = f"precise-{suffix}"
    denied = httpx.get(
        f"{BASE}/api/v1/geo/location",
        headers=h,
        params={"subject": precise_subject, "latitude": -33.9, "longitude": 18.4},
        timeout=20,
    )
    self_grant = httpx.post(
        f"{BASE}/api/v1/geo/permissions",
        headers=h,
        json={
            "subject": precise_subject,
            "precision": "precise",
            "purpose": "tracking",
            "granted_by": precise_subject,
        },
        timeout=20,
    )
    check("no covert precise tracking", denied.status_code == 200 and denied.json().get("permitted") is False and self_grant.status_code == 400, str(self_grant.status_code))

    owner_grant = httpx.post(
        f"{BASE}/api/v1/geo/permissions",
        headers=h,
        json={
            "subject": precise_subject,
            "precision": "precise",
            "purpose": "delivery",
            "granted_by": "owner",
        },
        timeout=20,
    )
    precise = httpx.get(
        f"{BASE}/api/v1/geo/location",
        headers=h,
        params={"subject": precise_subject, "latitude": -33.9, "longitude": 18.4},
        timeout=20,
    )
    check(
        "precise location needs explicit permission",
        owner_grant.status_code == 200 and precise.json().get("precision") == "precise",
        str(precise.json()),
    )

    st = httpx.get(f"{BASE}/api/v1/geo/status", headers=h, timeout=20)
    check("provider-independent knowledge", st.status_code == 200 and st.json().get("provider_independent_knowledge") is True, str(st.status_code))

    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Geospatial smoke summary ===\n{passed}/{len(results)} passed")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
