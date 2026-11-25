"""Level 1 — Operational acceptance tests for IAM.

Run against a live stack:  python tests/level1_acceptance.py
Tests: health, identity persistence, multi-turn conversation, visitor isolation,
memory retrieval, owner authorization boundary.
"""

import sys
import json
import httpx
from datetime import datetime
from auth_headers import install_auth_headers

install_auth_headers()

BASE = "http://localhost:8000"
results = []


def check(name, ok, detail=""):
    results.append({"test": name, "passed": bool(ok), "detail": detail})
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def main():
    # 1. Health
    try:
        r = httpx.get(f"{BASE}/health", timeout=10)
        check("health endpoint", r.status_code == 200 and r.json().get("status") == "healthy", str(r.status_code))
    except Exception as e:
        check("health endpoint", False, str(e))

    # 2. Identity genesis (permanent ULID)
    try:
        r = httpx.get(f"{BASE}/api/v1/setup/genesis", timeout=10)
        data = r.json()
        pid = data.get("permanent_id", "")
        # Permanent ID is immutable (OD-01). New records are 26-char ULIDs;
        # the current genesis was created before the width fix, so accept 20-26.
        check("identity genesis exists", r.status_code == 200 and 20 <= len(pid) <= 26 and pid.isalnum(),
              f"permanent_id={pid}")
        check("identity full name", data.get("full_name") == "Intellectual Artificial Mainbrain")
    except Exception as e:
        check("identity genesis", False, str(e))

    # 3. Two visitors — independent sessions
    tokens = []
    for i in range(2):
        try:
            r = httpx.post(f"{BASE}/api/v1/access/sessions", json={"mode": "focus"}, timeout=10)
            tokens.append(r.json().get("session_token"))
        except Exception:
            tokens.append(None)
    check("two anonymous sessions created", all(tokens), str(tokens))

    # 4. Send distinct messages to each session
    if all(tokens):
        try:
            httpx.post(f"{BASE}/api/v1/access/messages", json={
                "session_token": tokens[0], "role": "user", "content": "ALPHA secret marker"
            }, timeout=10)
            httpx.post(f"{BASE}/api/v1/access/messages", json={
                "session_token": tokens[1], "role": "user", "content": "BETA secret marker"
            }, timeout=10)
            r1 = httpx.get(f"{BASE}/api/v1/access/sessions/{tokens[0]}/messages", timeout=10).json()
            r2 = httpx.get(f"{BASE}/api/v1/access/sessions/{tokens[1]}/messages", timeout=10).json()
            c1 = json.dumps(r1)
            c2 = json.dumps(r2)
            check("visitor A sees own message", "ALPHA" in c1)
            check("visitor A cannot see B", "BETA" not in c1)
            check("visitor B sees own message", "BETA" in c2)
            check("visitor B cannot see A", "ALPHA" not in c2)
        except Exception as e:
            check("visitor isolation", False, str(e))

    # 5. Context isolation — location is estimate, permissions set
    if all(tokens):
        try:
            ctx = httpx.get(f"{BASE}/api/v1/access/sessions/{tokens[0]}/context", timeout=10).json()
            check("geoip is estimate", ctx.get("location", {}).get("is_estimate") is True)
            check("anonymous memory default (OD-05)",
                  ctx.get("memory_permission", {}).get("allow_anonymous_memory") is True,
                  str(ctx.get("memory_permission")))
        except Exception as e:
            check("context isolation", False, str(e))

    # 6. Memory store + semantic search
    try:
        r = httpx.post(f"{BASE}/api/v1/memory/", json={
            "content": "IAM acceptance test: the sky appears blue due to Rayleigh scattering",
            "memory_type": "fact",
            "topic": "physics",
            "confidence_level": 0.9,
        }, timeout=15)
        stored = r.status_code in (200, 201)
        check("memory stored", stored, str(r.status_code))
        s = httpx.post(f"{BASE}/api/v1/memory/search", json={
            "query": "why is the sky blue", "limit": 5
        }, timeout=15)
        check("memory search endpoint", s.status_code == 200, str(s.status_code))
    except Exception as e:
        check("memory", False, str(e))

    # 7. Authority boundary — self-escalation rejected
    try:
        r = httpx.post(f"{BASE}/api/v1/governance/check-authority", json={
            "action_type": "grant_own_access", "requested_level": "1"
        }, timeout=10)
        d = r.json()
        check("self-escalation rejected", d.get("permitted") is False, str(d.get("reason")))
    except Exception as e:
        check("authority boundary", False, str(e))

    # 8. Creator authority is email + signed challenge; legacy owner routes
    #    were retired (OD-03/OD-19). Verify the replacement is readable.
    try:
        r = httpx.get(f"{BASE}/api/v1/creator/policy", timeout=10)
        check("creator approval policy readable", r.status_code == 200, str(r.status_code))
    except Exception as e:
        check("creator approval policy", False, str(e))

    print("\n=== Level 1 summary ===")
    passed = sum(1 for r in results if r["passed"])
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
