"""Legal intelligence and government monitoring smoke test (OD-31).

IAM_ADMIN_KEY is used for the authorisation step; IAM_API_KEY is an operator
credential for research/monitoring calls.
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
    operator = os.environ.get("IAM_API_KEY", "")
    admin = os.environ.get("IAM_ADMIN_KEY", operator)
    if not operator:
        print("SKIP: set IAM_API_KEY")
        return
    op_h = {"Authorization": f"Bearer {operator}"}
    admin_h = {"Authorization": f"Bearer {admin}"}
    suffix = uuid.uuid4().hex[:8]

    s = httpx.post(
        f"{BASE}/api/v1/legal/sources",
        headers=op_h,
        json={
            "name": f"ZA Gov Gazette {suffix}",
            "jurisdiction": "ZA",
            "authority_type": "government",
            "url": "https://www.gov.za/gazette",
            "feed_url": "https://www.gov.za/gazette/feed",
            "reliability": "official",
        },
        timeout=20,
    )
    source_id = s.json().get("id")
    check("official source registered", s.status_code == 200 and bool(source_id), str(s.status_code))

    c1 = httpx.post(
        f"{BASE}/api/v1/legal/sources/{source_id}/check",
        headers=op_h,
        json={"content": "first snapshot"},
        timeout=20,
    )
    c2 = httpx.post(
        f"{BASE}/api/v1/legal/sources/{source_id}/check",
        headers=op_h,
        json={"content": "second snapshot with a new notice"},
        timeout=20,
    )
    check(
        "publication change detected from hash",
        c1.status_code == 200 and c2.json().get("changed") is True,
        str(c2.json().get("changed")),
    )

    i = httpx.post(
        f"{BASE}/api/v1/legal/instruments",
        headers=op_h,
        json={
            "source_id": source_id,
            "jurisdiction": "ZA",
            "title": f"Data Protection Amendment Bill {suffix}",
            "authority_name": "Parliament",
            "instrument_type": "bill",
            "status": "proposed",
            "official_url": "https://www.gov.za/bills/data-protection",
            "summary": "Proposed amendments to data protection obligations",
        },
        timeout=20,
    )
    instrument_id = i.json().get("id")
    check("legal instrument recorded with primary source", i.status_code == 200 and bool(instrument_id), str(i.status_code))

    ch = httpx.post(
        f"{BASE}/api/v1/legal/changes",
        headers=op_h,
        json={
            "instrument_id": instrument_id,
            "change_type": "new",
            "severity": "important",
            "evidence": {"official_url": "https://www.gov.za/bills/data-protection"},
        },
        timeout=20,
    )
    change_id = ch.json().get("id")
    check("change discovered with evidence", ch.status_code == 200 and ch.json().get("lifecycle_stage") == "discover", str(ch.status_code))

    au = httpx.post(f"{BASE}/api/v1/legal/changes/{change_id}/authenticate", headers=op_h, timeout=20)
    check("source authentication", au.status_code == 200 and au.json().get("authenticated") is True, str(au.json().get("authenticated")))

    un = httpx.post(
        f"{BASE}/api/v1/legal/changes/{change_id}/understand",
        headers=op_h,
        json={"summary": "Bill proposes changes to cross-border data sharing."},
        timeout=20,
    )
    check("legal change understood", un.status_code == 200, str(un.status_code))

    asr = httpx.post(
        f"{BASE}/api/v1/legal/changes/{change_id}/assess",
        headers=op_h,
        json={
            "impacts": [
                {
                    "affected_system": "privacy_and_memory",
                    "assessment": "Cross-border transfer rules may require review.",
                    "risk_level": "medium",
                    "recommendation": "Review retention and transfer controls.",
                    "obligations": [{"id": "ob-privacy", "description": "Review transfer controls", "status": "open"}],
                }
            ]
        },
        timeout=20,
    )
    impact_id = (asr.json().get("impacts") or [None])[0]
    check("impact assessment recorded", asr.status_code == 200 and bool(impact_id), str(asr.status_code))

    rc = httpx.post(
        f"{BASE}/api/v1/legal/changes/{change_id}/recommend",
        headers=op_h,
        json={"recommendations": ["Ask creator to approve privacy policy review"]},
        timeout=20,
    )
    check("recommendation stage", rc.status_code == 200, str(rc.status_code))

    no_ref = httpx.post(
        f"{BASE}/api/v1/legal/changes/{change_id}/authorise",
        headers=op_h,
        json={"creator_approval_reference": ""},
        timeout=20,
    )
    check("IAM cannot self-authorise", no_ref.status_code == 400, str(no_ref.status_code))

    auth = httpx.post(
        f"{BASE}/api/v1/legal/changes/{change_id}/authorise",
        headers=admin_h,
        json={"creator_approval_reference": "signed-request-legal-001"},
        timeout=20,
    )
    check("creator authorisation recorded", auth.status_code == 200, str(auth.status_code))

    impl = httpx.post(
        f"{BASE}/api/v1/legal/changes/{change_id}/implement",
        headers=op_h,
        json={"evidence": {"policy_revision": "隐私-policy-v2"}},
        timeout=20,
    )
    check("authorised change implemented", impl.status_code == 200, str(impl.status_code))

    ver = httpx.post(
        f"{BASE}/api/v1/legal/changes/{change_id}/verify",
        headers=op_h,
        json={"evidence": {"test": "transfer controls reviewed"}},
        timeout=20,
    )
    check("compliance verified with evidence", ver.status_code == 200 and ver.json().get("lifecycle_stage") == "verify", str(ver.status_code))

    obl = httpx.post(
        f"{BASE}/api/v1/legal/impacts/{impact_id}/obligations",
        headers=op_h,
        json={
            "obligation_id": "ob-privacy",
            "status": "completed",
            "evidence": {"review_id": "privacy-review-2026"},
        },
        timeout=20,
    )
    check("obligation evidence recorded", obl.status_code == 200 and obl.json().get("evidence_recorded") is True, str(obl.status_code))

    # High-impact interpretations require qualified professional review.
    ch2 = httpx.post(
        f"{BASE}/api/v1/legal/changes",
        headers=op_h,
        json={
            "instrument_id": instrument_id,
            "severity": "critical",
            "evidence": {"official_url": "https://www.gov.za/bills/data-protection"},
        },
        timeout=20,
    )
    cid2 = ch2.json().get("id")
    httpx.post(f"{BASE}/api/v1/legal/changes/{cid2}/authenticate", headers=op_h, timeout=20)
    httpx.post(
        f"{BASE}/api/v1/legal/changes/{cid2}/understand",
        headers=op_h,
        json={"summary": "Critical interpretation of new obligations"},
        timeout=20,
    )
    httpx.post(
        f"{BASE}/api/v1/legal/changes/{cid2}/assess",
        headers=op_h,
        json={
            "impacts": [
                {
                    "affected_system": "finance",
                    "assessment": "Possible unlawful transfer restrictions",
                    "risk_level": "high",
                    "recommendation": "Escalate to qualified counsel",
                }
            ]
        },
        timeout=20,
    )
    httpx.post(
        f"{BASE}/api/v1/legal/changes/{cid2}/recommend",
        headers=op_h,
        json={"recommendations":["Pause affected transfers pending review"]},
        timeout=20,
    )
    no_pro = httpx.post(
        f"{BASE}/api/v1/legal/changes/{cid2}/authorise",
        headers=admin_h,
        json={"creator_approval_reference": "signed-legal-002"},
        timeout=20,
    )
    check("high-impact review required", no_pro.status_code == 400, str(no_pro.status_code))
    with_pro = httpx.post(
        f"{BASE}/api/v1/legal/changes/{cid2}/authorise",
        headers=admin_h,
        json={
            "creator_approval_reference": "signed-legal-002",
            "professional_review_reference": "qualified-counsel-2026",
        },
        timeout=20,
    )
    check("professional review enables authorisation", with_pro.status_code == 200, str(with_pro.status_code))

    am = httpx.post(
        f"{BASE}/api/v1/legal/instruments/{instrument_id}/amend",
        headers=op_h,
        json={"summary": "Amended bill text", "reason": "official revised version"},
        timeout=20,
    )
    check("amendment preserves version history", am.status_code == 200 and am.json().get("previous_versions_preserved") is True, str(am.status_code))

    alerts = httpx.get(f"{BASE}/api/v1/legal/alerts", headers=op_h, timeout=20)
    check("prioritised alerts available", alerts.status_code == 200 and len(alerts.json().get("alerts", [])) >= 2, str(alerts.status_code))

    st = httpx.get(f"{BASE}/api/v1/legal/status", headers=op_h, timeout=20)
    check("legal research is not legal advice", st.status_code == 200 and st.json().get("claim") == "legal_research_not_legal_advice", str(st.status_code))

    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Legal intelligence smoke summary ===\n{passed}/{len(results)} passed")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
