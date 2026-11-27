"""Opt-in live smoke test for the IICS overlay.

Never runs in CI. Requires a live stack, an admin credential and the IICS
migration applied:

    IAM_IICS_SMOKE=1 IAM_API_KEY=<key> python tests/iics_live_smoke.py

A skipped run prints SKIPPED and no IAM_IICS_OK. A failed run exits non-zero.
"""

from __future__ import annotations

import os

import httpx
from auth_headers import install_auth_headers

install_auth_headers()

BASE = os.environ.get("IAM_BASE_URL", "http://localhost:8000")
ROOT = f"{BASE}/api/v1/iics"
results: list[tuple[str, bool]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    if os.environ.get("IAM_IICS_SMOKE") != "1" or not os.environ.get("IAM_API_KEY"):
        print("SKIPPED: set IAM_IICS_SMOKE=1 and IAM_API_KEY to run the live IICS smoke")
        return 0

    try:
        with httpx.Client(timeout=45) as client:
            blocked = client.post(f"{ROOT}/egress/check", json={"url": "http://127.0.0.1/"})
            check("egress rejects loopback", blocked.status_code == 200 and not blocked.json().get("allowed"))

            allowed = client.post(f"{ROOT}/egress/check", json={"url": "https://example.com"})
            check("egress allows public host", allowed.status_code == 200 and bool(allowed.json().get("allowed")))

            auth = client.post(
                f"{ROOT}/authorize",
                json={"action_type": "browse_public", "url": "https://example.com"},
            )
            auth_body = auth.json() if auth.status_code == 200 else {}
            check(
                "free public research is autonomous",
                auth.status_code == 200
                and auth_body.get("permitted") is True
                and auth_body.get("approval_required") is False,
                str(auth_body.get("reason") or auth.status_code),
            )

            tools = client.post(f"{ROOT}/tools/register")
            check("IICS tools registered", tools.status_code == 200 and len(tools.json()) >= 8)

            qa = client.post(f"{ROOT}/qa/run")
            check("QA suite runs", qa.status_code == 200 and bool(qa.json().get("results")))

            results_read = client.get(f"{ROOT}/qa/results")
            check(
                "QA results persisted",
                results_read.status_code == 200 and len(results_read.json()) >= 4,
            )

            scheduled = client.post(
                f"{ROOT}/scheduled",
                json={
                    "goal": "smoke",
                    "query": "example domain",
                    "cadence_minutes": 1440,
                    "task_id": "iics-live-smoke",
                },
            )
            check("scheduled task created", scheduled.status_code in (200, 201))

            listed = client.get(f"{ROOT}/scheduled")
            check(
                "scheduled task readable",
                listed.status_code == 200
                and any(item.get("task_id") == "iics-live-smoke" for item in listed.json()),
            )

            advisories = client.get(f"{ROOT}/security/advisories")
            check("advisory endpoint available", advisories.status_code == 200)

            policies = client.get(f"{ROOT}/site-policies/stale")
            check("site-policy endpoint available", policies.status_code == 200)
    except Exception as exc:  # noqa: BLE001 - smoke runner reports any failure
        check("live request sequence", False, f"{type(exc).__name__}: {exc}")

    ok = all(passed for _, passed in results)
    if ok:
        print("IAM_IICS_OK")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
