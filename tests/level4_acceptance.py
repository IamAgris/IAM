"""Level 4 — Distributed acceptance tests for IAM.

Run: python tests/level4_acceptance.py
Tests: permanent identity, creator authority boundaries, P2P agent trust model,
restricted reporting semantics, offline knowledge sync readiness, resilience,
architecture metadata (ARM64/x86-64 readiness).
"""

import sys
import platform
import httpx

BASE = "http://localhost:8000"
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main():
    # 1. Permanent identity (OD-01)
    try:
        g = httpx.get(f"{BASE}/api/v1/setup/genesis", timeout=10).json()
        check("permanent identity exists", bool(g.get("permanent_id")))
        check("identity creator authority", g.get("origin_config", {}).get("creator_authority") == "protected_core")
    except Exception as e:
        check("permanent identity", False, str(e))

    # 2. Security boundaries immutable (OD-11)
    try:
        b = httpx.get(f"{BASE}/api/v1/governance/security-boundaries", timeout=10).json()
        check("security boundaries defined", len(b) >= 3, f"{len(b)} boundaries")
        check("boundaries immutable", all(x.get("is_immutable") for x in b))
    except Exception as e:
        check("security boundaries", False, str(e))

    # 3. Self-escalation blocked across levels
    for action in ["modify_security_boundaries", "grant_own_access", "spend_money", "transfer_money"]:
        try:
            r = httpx.post(f"{BASE}/api/v1/governance/check-authority", json={
                "action_type": action, "requested_level": "1"
            }, timeout=10)
            check(f"blocked: {action}", r.json().get("permitted") is False)
        except Exception as e:
            check(f"blocked: {action}", False, str(e))

    # 4. P2P agent registry — untrusted by default
    agent_id = None
    try:
        r = httpx.post(f"{BASE}/api/v1/network/agents", json={
            "name": "L4 dist test", "endpoint_url": "https://example.invalid/agent",
            "protocol": "rest", "capabilities": ["research"]
        }, timeout=10)
        agent_id = r.json().get("id")
        check("peer registered", r.status_code == 200 and agent_id is not None)
    except Exception as e:
        check("peer registered", False, str(e))

    if agent_id:
        try:
            agents = httpx.get(f"{BASE}/api/v1/network/agents", timeout=10).json()
            a = next(x for x in agents if x["id"] == agent_id)
            check("peer zero trust", a.get("trust_score") == 0.0)
            check("peer inactive until attested", a.get("is_active") is False)
        except Exception as e:
            check("peer trust state", False, str(e))

        # Trust assessment updates score
        try:
            r = httpx.post(f"{BASE}/api/v1/network/trust", json={
                "agent_id": agent_id, "assessment": "helpful", "trust_delta": 0.3
            }, timeout=10)
            check("trust assessment recorded", r.status_code == 200 and r.json().get("new_trust_score") is not None)
        except Exception as e:
            check("trust assessment", False, str(e))

        # Block untrusted agent (restricted/revoked capability)
        try:
            r = httpx.patch(f"{BASE}/api/v1/network/agents/{agent_id}/status", json={"status": "blocked"}, timeout=10)
            check("peer can be blocked", r.status_code == 200 and r.json().get("status") == "blocked")
        except Exception as e:
            check("peer block", False, str(e))

    # 5. Restricted reporting — message to blocked agent refused
    if agent_id:
        try:
            r = httpx.post(f"{BASE}/api/v1/network/agents/{agent_id}/message", json={
                "agent_id": agent_id, "message": "test"
            }, timeout=10)
            check("blocked peer refuses traffic", r.status_code == 400 or r.json().get("success") is False)
        except Exception as e:
            check("blocked peer traffic", False, str(e))

    # 6. Interaction audit trail
    try:
        r = httpx.get(f"{BASE}/api/v1/network/interactions", timeout=10)
        check("interaction audit available", r.status_code == 200 and isinstance(r.json(), list))
    except Exception as e:
        check("interaction audit", False, str(e))

    # 7. Collaboration requires authorization for high-impact
    try:
        r = httpx.post(f"{BASE}/api/v1/network/collaborations", json={
            "agent_id": agent_id or "00000000-0000-0000-0000-000000000000",
            "task_description": "L4 test delegation", "requires_authorization": True
        }, timeout=10)
        d = r.json()
        check("delegation flagged for authorization", r.status_code == 200 and d.get("requires_authorization") is True)
    except Exception as e:
        check("collaboration authorization", False, str(e))

    # 8. Resilience — backup verification + incident reporting
    try:
        r = httpx.post(f"{BASE}/api/v1/resilience/backup-verify", json={
            "backup_id": "l4-test-backup", "verification_type": "integrity", "success": True
        }, timeout=10)
        check("backup verification recorded", r.status_code == 200)
    except Exception as e:
        check("backup verification", False, str(e))

    try:
        r = httpx.post(f"{BASE}/api/v1/resilience/incidents", json={
            "incident_type": "security", "severity": "low", "title": "L4 test incident"
        }, timeout=10)
        check("incident recorded", r.status_code == 200)
    except Exception as e:
        check("incident recorded", False, str(e))

    # 9. Architecture portability metadata
    check("runtime architecture detected",
          platform.machine().lower() in ("x86_64", "amd64", "aarch64", "arm64"),
          platform.machine())
    try:
        r = httpx.get(f"{BASE}/api/v1/models/router/providers", timeout=10)
        check("provider abstraction available", r.status_code == 200)
    except Exception as e:
        check("provider abstraction", False, str(e))

    print("\n=== Level 4 summary ===")
    passed = sum(1 for r in results if r[1])
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
