"""UWAIE + core-authorised storage smoke test (OD-27, OD-29).

Run against a live stack with a scoped API credential:
    IAM_API_KEY=<key> python tests/uwaie_storage_smoke.py
"""

import base64
import os
import urllib.parse
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
        print("SKIP: set IAM_API_KEY to run this live-stack test")
        return

    # Core-authorised S3 storage roundtrip.
    name = f"smoke-{uuid.uuid4().hex[:8]}.txt"
    content = "UWAIE storage smoke test"
    r = httpx.post(
        f"{BASE}/api/v1/storage/objects",
        json={"name": name, "content": content, "content_type": "text/plain"},
        timeout=20,
    )
    obj = r.json()
    check("storage upload", r.status_code == 200 and bool(obj.get("id")), str(r.status_code))
    if obj.get("id"):
        g = httpx.get(f"{BASE}/api/v1/storage/objects/{obj['id']}", timeout=20)
        decoded = (
            base64.b64decode(g.json().get("content_base64", "")).decode()
            if g.status_code == 200
            else ""
        )
        check("storage retrieval + checksum", decoded == content, str(g.status_code))

    # Isolated session.
    s = httpx.post(f"{BASE}/api/v1/uwaie/sessions", json={"purpose": "smoke"}, timeout=20)
    token = s.json().get("session_token")
    check("isolated browsing session", s.status_code == 200 and bool(token), str(s.status_code))

    html = "<html><body><h1>IAM UWAIE OK</h1><form><input name=q aria-label=query></form></body></html>"
    url = "data:text/html," + urllib.parse.quote(html)

    i = httpx.post(f"{BASE}/api/v1/uwaie/inspect", json={"url": url}, timeout=60)
    check("frontend inspection", i.status_code == 200 and len(i.json().get("forms", [])) == 1, str(i.status_code))

    steps = [
        {"action": "navigate", "target": url},
        {"action": "type", "target": "input[name=q]", "value": "secret-value"},
        {"action": "text", "target": "body"},
    ]
    wf_name = f"smoke-workflow-{uuid.uuid4().hex[:8]}"
    e = httpx.post(
        f"{BASE}/api/v1/uwaie/execute",
        json={
            "steps": steps,
            "verification": {"expected_text": "IAM UWAIE OK"},
            "session_token": token,
            "learn": True,
            "workflow_name": wf_name,
        },
        timeout=60,
    )
    outcome = e.json()
    check("verified execution", e.status_code == 200 and outcome.get("verified") is True, str(e.status_code))

    workflow_response = httpx.get(f"{BASE}/api/v1/uwaie/workflows", timeout=20)
    workflows = workflow_response.json()
    if not isinstance(workflows, list):
        workflows = []
    entry = next((w for w in workflows if w.get("name") == wf_name), None)
    typed = [st.get("value") for st in entry["steps"] if st.get("action") == "type"] if entry else []
    check("credential-free workflow knowledge", typed == ["<redacted>"], str(typed))

    blocked = httpx.post(
        f"{BASE}/api/v1/uwaie/execute",
        json={
            "steps": [{"action": "navigate", "target": "https://example.com/captcha"}],
            "verification": {},
            "session_token": token,
        },
        timeout=20,
    )
    check("captcha bypass rejected", blocked.status_code == 400, str(blocked.status_code))

    gated = httpx.post(
        f"{BASE}/api/v1/uwaie/execute",
        json={
            "steps": [{"action": "submit", "target": "https://example.com/form"}],
            "verification": {},
            "session_token": token,
        },
        timeout=20,
    )
    check("submit gated by signed authorization", gated.status_code == 400, str(gated.status_code))

    passed = sum(1 for _, ok in results if ok)
    print(f"\n=== UWAIE/storage smoke summary ===\n{passed}/{len(results)} passed")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
