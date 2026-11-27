"""Human Public Presence Intelligence smoke test (OD-30 / PPIICE)."""

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

    b = httpx.get(f"{BASE}/api/v1/human-presence/boundaries", headers=h, timeout=20)
    rules = b.json().get("rules", [])
    check(
        "privacy boundaries published",
        b.status_code == 200
        and "no_deanonymisation" in rules
        and "no_visitor_memory_or_credentials" in rules,
        str(rules),
    )

    p = httpx.post(
        f"{BASE}/api/v1/human-presence/people",
        headers=h,
        json={"canonical_name": f"Ada Public {suffix}", "notes": "public researcher"},
        timeout=20,
    )
    person_id = p.json().get("id")
    check(
        "public person created without identity claim",
        p.status_code == 200 and p.json().get("deanonymized") is False,
        str(p.status_code),
    )

    bad = httpx.post(
        f"{BASE}/api/v1/human-presence/people",
        headers=h,
        json={"canonical_name": "Hidden", "deanonymize": True},
        timeout=20,
    )
    check("de-anonymisation request rejected", bad.status_code in (400, 422), str(bad.status_code))

    visitor = httpx.post(
        f"{BASE}/api/v1/human-presence/people",
        headers=h,
        json={"canonical_name": "Someone", "notes": "visitor_memory dump"},
        timeout=20,
    )
    check("visitor memory cannot be used as a source", visitor.status_code == 400, str(visitor.status_code))

    profile1 = httpx.post(
        f"{BASE}/api/v1/human-presence/profiles",
        headers=h,
        json={
            "person_id": person_id,
            "source_name": "Personal site",
            "source_url": f"https://ada.example/{suffix}",
            "profile_type": "personal_site",
            "stated_name": "Ada",
            "role": "Researcher",
            "interests": ["systems", "robotics"],
        },
        timeout=20,
    )
    profile_id = profile1.json().get("id")
    check("self-reported profile stored as untrusted", profile1.status_code == 200 and profile1.json().get("status") == "self_reported", str(profile1.status_code))

    early = httpx.post(
        f"{BASE}/api/v1/human-presence/profiles/{profile_id}/verify",
        headers=h,
        timeout=20,
    )
    check("single source cannot verify a profile", early.status_code == 400, str(early.status_code))

    httpx.post(
        f"{BASE}/api/v1/human-presence/profiles",
        headers=h,
        json={
            "person_id": person_id,
            "source_name": "Professional profile",
            "source_url": f"https://profiles.example/ada/{suffix}",
            "profile_type": "professional_profile",
            "stated_name": "Ada Public",
            "organization": "Example Lab",
        },
        timeout=20,
    )
    verified = httpx.post(
        f"{BASE}/api/v1/human-presence/profiles/{profile_id}/verify",
        headers=h,
        timeout=20,
    )
    check(
        "cross-source verification is public equivalence",
        verified.status_code == 200
        and verified.json().get("claim") == "public_profile_equivalence_not_real_world_identity",
        str(verified.json()),
    )

    claim = httpx.post(
        f"{BASE}/api/v1/human-presence/claims",
        headers=h,
        json={
            "person_id": person_id,
            "profile_id": profile_id,
            "claim_type": "role",
            "value": {"title": "Researcher"},
            "status": "self_reported",
            "source_url": f"https://ada.example/{suffix}",
        },
        timeout=20,
    )
    claim_id = claim.json().get("id")
    check("public role claim stored", claim.status_code == 200 and bool(claim_id), str(claim.status_code))

    sensitive = httpx.post(
        f"{BASE}/api/v1/human-presence/claims",
        headers=h,
        json={"person_id": person_id, "claim_type": "religion", "value": {"belief": "x"}},
        timeout=20,
    )
    check("sensitive trait inference rejected", sensitive.status_code == 400, str(sensitive.status_code))

    p2 = httpx.post(
        f"{BASE}/api/v1/human-presence/people",
        headers=h,
        json={"canonical_name": f"A. Public {suffix}"},
        timeout=20,
    )
    other_id = p2.json().get("id")
    match = httpx.post(
        f"{BASE}/api/v1/human-presence/people/{person_id}/match",
        headers=h,
        json={
            "other_id": other_id,
            "evidence": {
                "personal_site": f"https://ada.example/{suffix}",
                "professional_profile": f"https://profiles.example/ada/{suffix}",
            },
            "confidence": 0.95,
        },
        timeout=20,
    )
    check(
        "identity match is probabilistic public equivalence",
        match.status_code == 200
        and match.json().get("result") in {"same", "uncertain"}
        and match.json().get("claim") == "public_profile_equivalence_only",
        str(match.json()),
    )

    rel = httpx.post(
        f"{BASE}/api/v1/human-presence/relationships",
        headers=h,
        json={
            "person_id": person_id,
            "organization_name": "Example Lab",
            "relationship_type": "affiliation",
            "evidence": {"source": f"https://profiles.example/ada/{suffix}"},
        },
        timeout=20,
    )
    check("public affiliation recorded with evidence", rel.status_code == 200, str(rel.status_code))

    corrected = httpx.post(
        f"{BASE}/api/v1/human-presence/claims/{claim_id}/corrections",
        headers=h,
        json={"value": {"title": "Senior Researcher"}, "reason": "profile updated"},
        timeout=20,
    )
    claims = httpx.get(
        f"{BASE}/api/v1/human-presence/people/{person_id}/claims", headers=h, timeout=20
    ).json()
    old = next(c for c in claims if c["id"] == claim_id)
    check(
        "correction preserves original claim",
        corrected.status_code == 200
        and corrected.json().get("original_preserved") is True
        and old["status"] == "corrected",
        str(old["status"]),
    )

    timeline = httpx.get(
        f"{BASE}/api/v1/human-presence/people/{person_id}/timeline", headers=h, timeout=20
    )
    check(
        "dated source-backed timeline",
        timeline.status_code == 200
        and len(timeline.json().get("items", [])) >= 2
        and all("source_url" in item for item in timeline.json()["items"]),
        str(len(timeline.json().get("items", []))),
    )

    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Human presence smoke summary ===\n{passed}/{len(results)} passed")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
