"""AI Assistant Interoperability and Technology Learning smoke test (OD-28)."""

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

    b = httpx.get(f"{BASE}/api/v1/assistant-lab/boundaries", headers=h, timeout=20)
    check(
        "internal research boundaries published",
        b.status_code == 200
        and b.json().get("claim") == "internal_research_not_user_feature"
        and "vendor_dependency" in b.json().get("prohibited", []),
        str(b.status_code),
    )

    systems = {}
    for name, vendor, docs in [
        (f"Alexa {suffix}", "Amazon", "https://developer.amazon.com/alexa"),
        (f"Siri {suffix}", "Apple", "https://developer.apple.com/app-intents/"),
        (f"Bixby {suffix}", "Samsung", "https://developer.samsung.com/automation"),
    ]:
        r = httpx.post(
            f"{BASE}/api/v1/assistant-lab/systems",
            headers=h,
            json={
                "name": name,
                "vendor": vendor,
                "official_docs_url": docs,
                "public_capabilities": ["voice", "intents"],
            },
            timeout=20,
        )
        systems[name] = (r.json().get("id"), docs)
    check("assistant systems registered from public docs", all(v[0] for v in systems.values()), str(len(systems)))

    bad = httpx.post(
        f"{BASE}/api/v1/assistant-lab/systems",
        headers=h,
        json={
            "name": f"Private {suffix}",
            "vendor": "x",
            "official_docs_url": "https://example.invalid/docs?model=proprietary_weights",
        },
        timeout=20,
    )
    check("private model access rejected", bad.status_code == 400, str(bad.status_code))

    alexa_id, alexa_docs = list(systems.values())[0]
    note = httpx.post(
        f"{BASE}/api/v1/assistant-lab/notes",
        headers=h,
        json={
            "assistant_id": alexa_id,
            "topic": "speech_recognition",
            "observation": "Public docs describe an intent and slot model.",
            "source_url": alexa_docs,
            "status": "verified",
            "confidence": 0.8,
        },
        timeout=20,
    )
    check("public research note stored", note.status_code == 200 and note.json().get("status") == "verified", str(note.status_code))

    unverified = httpx.post(
        f"{BASE}/api/v1/assistant-lab/notes",
        headers=h,
        json={
            "assistant_id": alexa_id,
            "topic": "speech_recognition",
            "observation": "Unofficial blog claim",
            "source_url": "https://blog.example.invalid/post",
            "status": "verified",
        },
        timeout=20,
    )
    check("unofficial source cannot be marked verified", unverified.status_code == 400, str(unverified.status_code))

    private_note = httpx.post(
        f"{BASE}/api/v1/assistant-lab/notes",
        headers=h,
        json={
            "assistant_id": alexa_id,
            "topic": "intent_execution",
            "observation": "internal_reasoning trace was observed",
            "source_url": alexa_docs,
        },
        timeout=20,
    )
    check("private reasoning research rejected", private_note.status_code == 400, str(private_note.status_code))

    adapter = httpx.post(
        f"{BASE}/api/v1/assistant-lab/adapters",
        headers=h,
        json={
            "assistant_id": alexa_id,
            "name": "Alexa skill adapter",
            "interface_type": "official_skill",
        },
        timeout=20,
    )
    check(
        "official-interface adapter stores no credentials",
        adapter.status_code == 200
        and adapter.json().get("credentials_stored") is False
        and adapter.json().get("is_active") is False,
        str(adapter.status_code),
    )

    bad_adapter = httpx.post(
        f"{BASE}/api/v1/assistant-lab/adapters",
        headers=h,
        json={
            "assistant_id": alexa_id,
            "name": "Bad adapter",
            "interface_type": "official_api",
            "endpoint_template": "https://example.invalid?api_key=SECRET",
        },
        timeout=20,
    )
    check("embedded secret in adapter rejected", bad_adapter.status_code == 400, str(bad_adapter.status_code))

    exp = httpx.post(
        f"{BASE}/api/v1/assistant-lab/experiments",
        headers=h,
        json={
            "capability": "wake_word_detection",
            "hypothesis": "A small local model can detect a chosen wake word.",
            "method": "isolated Python audio experiment",
        },
        timeout=20,
    )
    exp_id = exp.json().get("id")
    check("replication experiment isolated", exp.status_code == 200 and exp.json().get("isolated") is True, str(exp.status_code))

    res = httpx.post(
        f"{BASE}/api/v1/assistant-lab/experiments/{exp_id}/result",
        headers=h,
        json={"result": "succeeded", "evidence": {"accuracy": 0.91}},
        timeout=20,
    )
    check("experiment result recorded with evidence", res.status_code == 200 and res.json().get("result") == "succeeded", str(res.status_code))

    no_ref = httpx.post(
        f"{BASE}/api/v1/assistant-lab/experiments/{exp_id}/adopt",
        headers=h,
        json={"creator_approval_reference": ""},
        timeout=20,
    )
    check("self-adoption blocked", no_ref.status_code == 400, str(no_ref.status_code))

    adopted = httpx.post(
        f"{BASE}/api/v1/assistant-lab/experiments/{exp_id}/adopt",
        headers=h,
        json={"creator_approval_reference": "signed-assistant-lab-001"},
        timeout=20,
    )
    check(
        "adoption builds IAM's own capability",
        adopted.status_code == 200 and "no vendor identity" in adopted.json().get("note", ""),
        str(adopted.status_code),
    )

    cmp = httpx.post(
        f"{BASE}/api/v1/assistant-lab/comparisons",
        headers=h,
        json={
            "assistant_id": alexa_id,
            "capability": "intent_execution",
            "rating": 4,
            "evidence_note": "public documentation describes structured intents",
        },
        timeout=20,
    )
    check("capability comparison recorded", cmp.status_code == 200 and cmp.json().get("assistant_id") == alexa_id, str(cmp.json()))

    st = httpx.get(f"{BASE}/api/v1/assistant-lab/status", headers=h, timeout=20)
    check(
        "lab is internal and vendor-independent",
        st.status_code == 200
        and st.json().get("internal_capability") is True
        and st.json().get("claim") == "no_vendor_dependency",
        str(st.status_code),
    )

    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== Assistant lab smoke summary ===\n{passed}/{len(results)} passed")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
