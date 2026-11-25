"""Public records / vital events / estate research smoke test (OD-30).

Run with a scoped API credential: IAM_API_KEY=<key> python tests/public_records_smoke.py
"""

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

    suffix = uuid.uuid4().hex[:8]

    s = httpx.post(
        f"{BASE}/api/v1/public-records/sources",
        json={
            "name": f"CIPC-{suffix}",
            "jurisdiction": "ZA",
            "category": "business",
            "url": "https://example.org/registry",
            "access_condition": "public",
            "reliability": "official",
            "terms_url": "https://example.org/terms",
        },
        timeout=20,
    )
    source_id = s.json().get("id")
    check("official source registered", s.status_code == 200 and bool(source_id), str(s.status_code))

    r = httpx.post(
        f"{BASE}/api/v1/public-records/records",
        json={
            "source_id": source_id,
            "category": "business",
            "jurisdiction": "ZA",
            "subject_name": f"Test Company {suffix}",
            "title": "Registration notice",
            "facts": {"status": "active", "registration_number": "2026/0001"},
            "status": "verified",
            "confidence": 0.9,
        },
        timeout=20,
    )
    record_id = r.json().get("id")
    check("verified record ingested with provenance", r.status_code == 200 and bool(r.json().get("content_hash")), str(r.status_code))

    a = httpx.post(
        f"{BASE}/api/v1/public-records/records",
        json={
            "source_id": source_id,
            "category": "court",
            "jurisdiction": "ZA",
            "title": "Unverified allegation",
            "facts": {"conviction": True},
            "status": "allegation",
            "confidence": 0.99,
        },
        timeout=20,
    )
    check(
        "allegation cannot be recorded as conviction",
        a.status_code == 400,
        str(a.status_code),
    )

    a2 = httpx.post(
        f"{BASE}/api/v1/public-records/records",
        json={
            "source_id": source_id,
            "category": "court",
            "jurisdiction": "ZA",
            "title": "Public allegation report",
            "facts": {"claim": "unverified"},
            "status": "allegation",
            "confidence": 0.99,
        },
        timeout=20,
    )
    check(
        "allegation confidence capped",
        a2.status_code == 200 and a2.json().get("confidence") == 0.5,
        str(a2.json().get("confidence")),
    )

    gated = httpx.post(
        f"{BASE}/api/v1/public-records/records",
        json={
            "source_id": source_id,
            "category": "estate_probate",
            "jurisdiction": "ZA",
            "title": "Private estate file",
            "facts": {"beneficiary": "individual"},
        },
        timeout=20,
    )
    check("estate record gated without authority", gated.status_code == 400, str(gated.status_code))

    permitted = httpx.post(
        f"{BASE}/api/v1/public-records/records",
        json={
            "source_id": source_id,
            "category": "estate_probate",
            "jurisdiction": "ZA",
            "title": "Estate notice",
            "facts": {"executor": "named"},
            "legal_authority_reference": "court-case-2026",
        },
        timeout=20,
    )
    check("estate record with authority accepted", permitted.status_code == 200, str(permitted.status_code))

    search = httpx.get(
        f"{BASE}/api/v1/public-records/records",
        params={"subject_name": f"Test Company {suffix}"},
        timeout=20,
    )
    check("provenance-preserving search", search.status_code == 200 and search.json().get("count") == 1, str(search.json().get("count")))

    conflict_id = a2.json().get("id")
    x = httpx.post(
        f"{BASE}/api/v1/public-records/records/{record_id}/cross-reference",
        json={
            "other_id": conflict_id,
            "relation_type": "conflict",
            "evidence": {"reason": "different claims about the same subject"},
            "confidence": 0.4,
        },
        timeout=20,
    )
    check("conflict stored without forced conclusion", x.status_code == 200 and x.json().get("relation_type") == "conflict", str(x.status_code))

    c = httpx.post(
        f"{BASE}/api/v1/public-records/records/{record_id}/corrections",
        json={
            "facts": {"status": "deregistered", "correction_of": record_id},
            "reason": "registry later updated the company status",
            "confidence": 0.95,
        },
        timeout=20,
    )
    check("correction appended", c.status_code == 200 and c.json().get("original_preserved") is True, str(c.status_code))

    rel = httpx.get(
        f"{BASE}/api/v1/public-records/records/{record_id}/relationships",
        timeout=20,
    )
    types = {r["relation_type"] for r in rel.json().get("relationships", [])}
    check("history retains conflict and correction", types == {"conflict", "correction"}, str(types))

    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Public records smoke summary ===\n{passed}/{len(results)} passed")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
