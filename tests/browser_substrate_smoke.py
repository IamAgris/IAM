"""Live browser substrate smoke test (Doc 29 P1 / WP-06).

Verifies real Playwright navigation and interaction through the standard
/api/v1/browser envelope: task ID, evidence refs and attribution. Never runs
in CI; requires an explicit opt-in and a live stack with an admin credential.

    IAM_BROWSER_SMOKE=1 IAM_API_KEY=<key> python tests/browser_substrate_smoke.py

A skipped run prints SKIPPED. A failed run never prints IAM_BROWSER_P1_OK.
"""

import os
import uuid

import httpx
from auth_headers import install_auth_headers

install_auth_headers()

BASE = os.environ.get("IAM_BASE_URL", "http://localhost:8000")
TARGET = os.environ.get("IAM_BROWSER_SMOKE_URL", "https://example.com")
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main():
    if os.environ.get("IAM_BROWSER_SMOKE") != "1" or not os.environ.get("IAM_API_KEY"):
        print("SKIPPED: set IAM_BROWSER_SMOKE=1 and IAM_API_KEY to run the live browser smoke")
        # Skip is not a pass claim (no IAM_BROWSER_P1_OK is printed), but it is
        # also not a failed test — callers should not treat opt-out as failure.
        return True

    task_id = f"browser-smoke-{uuid.uuid4().hex[:10]}"
    session_token = None
    with httpx.Client(timeout=45) as client:
        opened = client.post(
            f"{BASE}/api/v1/browser/sessions",
            json={"purpose": "phase1-smoke", "mode": "headless"},
        )
        check("session opened", opened.status_code == 200, str(opened.status_code))
        if opened.status_code != 200:
            return False
        session_token = opened.json().get("session_token")

        queued = client.post(
            f"{BASE}/api/v1/browser/tasks",
            json={
                "task_id": task_id,
                "session_token": session_token,
                "steps": [
                    {"action": "navigate", "target": TARGET},
                    {"action": "text", "target": "body"},
                ],
                "verification": {"expected_text": "This domain is for use"},
                "actor": "browser-smoke",
                "actor_type": "agent",
                "permission_scope": "browse_public",
            },
        )
        check("task submitted", queued.status_code in (200, 202), str(queued.status_code))
        if queued.status_code not in (200, 202):
            return False
        envelope = queued.json()
        check("task id propagated", envelope.get("task_id") == task_id)
        check("actor attributed", envelope.get("actor") == "browser-smoke")

        fetched = client.get(f"{BASE}/api/v1/browser/tasks/{task_id}")
        final = fetched.json() if fetched.status_code == 200 else {}
        check("task status recorded", final.get("status") in ("queued", "completed", "verifying"),
              str(final.get("status")))

        evidence = client.get(f"{BASE}/api/v1/browser/tasks/{task_id}/evidence")
        items = evidence.json() if evidence.status_code == 200 else []
        check("evidence preserved", isinstance(items, list) and len(items) > 0,
              f"{len(items) if isinstance(items, list) else 0} items")

        blocked = client.post(
            f"{BASE}/api/v1/browser/inspect",
            json={"url": "https://example.com/captcha-challenge", "actor": "browser-smoke"},
        )
        check("captcha target rejected", blocked.status_code == 400, str(blocked.status_code))

        if session_token:
            closed = client.delete(f"{BASE}/api/v1/browser/sessions/{session_token}")
            check("session closed", closed.status_code == 200, str(closed.status_code))

    ok = all(passed for _, passed in results)
    if ok:
        print("IAM_BROWSER_P1_OK")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
