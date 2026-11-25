"""Level 2 — Independent acceptance tests for IAM.

Run against live stack:  python tests/level2_acceptance.py
Tests: autonomous goal->plan->task lifecycle, decision records, authority
enforcement, research workflow with provenance, internet permission gates,
external AI network trust boundaries, background worker.
"""

import sys
import httpx
from auth_headers import install_auth_headers

install_auth_headers()

BASE = "http://localhost:8000"
results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def main():
    # 1. Goal creation
    goal_id = None
    try:
        r = httpx.post(f"{BASE}/api/v1/autonomy/goals/", json={
            "title": "L2 test goal", "description": "Acceptance test", "priority": 5
        }, timeout=10)
        goal_id = r.json().get("id")
        check("goal created", r.status_code == 200 and goal_id is not None, str(goal_id))
    except Exception as e:
        check("goal created", False, str(e))

    # 2. Plan linked to goal
    plan_id = None
    if goal_id:
        try:
            r = httpx.post(f"{BASE}/api/v1/autonomy/goals/plans", json={
                "goal_id": goal_id, "title": "L2 test plan",
                "steps": [{"action": "research"}, {"action": "execute"}]
            }, timeout=10)
            plan_id = r.json().get("id")
            check("plan linked to goal", r.status_code == 200 and plan_id is not None)
        except Exception as e:
            check("plan linked to goal", False, str(e))

    # 3. Task lifecycle
    task_id = None
    if plan_id:
        try:
            r = httpx.post(f"{BASE}/api/v1/autonomy/tasks/", json={
                "title": "L2 test task", "plan_id": plan_id
            }, timeout=10)
            task_id = r.json().get("id")
            check("task created", r.status_code == 200 and task_id is not None)
        except Exception as e:
            check("task created", False, str(e))

    # 4. Task status transitions
    if task_id:
        try:
            r = httpx.patch(f"{BASE}/api/v1/autonomy/tasks/{task_id}", json={"status": "in_progress"}, timeout=10)
            d = r.json()
            check("task -> in_progress", d.get("status") == "in_progress" and d.get("started_at") is not None)
            r = httpx.patch(f"{BASE}/api/v1/autonomy/tasks/{task_id}", json={"status": "completed"}, timeout=10)
            d = r.json()
            check("task -> completed", d.get("status") == "completed" and d.get("completed_at") is not None)
        except Exception as e:
            check("task lifecycle", False, str(e))

    # 5. Task execution record
    if task_id:
        try:
            r = httpx.post(f"{BASE}/api/v1/autonomy/tasks/executions", json={
                "task_id": task_id, "status": "success", "output": "L2 acceptance", "duration_ms": 12
            }, timeout=10)
            check("execution recorded", r.status_code == 200)
        except Exception as e:
            check("execution recorded", False, str(e))

    # 6. Decision record + review
    decision_id = None
    try:
        r = httpx.post(f"{BASE}/api/v1/autonomy/decisions/", json={
            "decision": "Test autonomous decision", "reasoning": "L2 acceptance", "confidence": 0.8
        }, timeout=10)
        decision_id = r.json().get("id")
        check("decision recorded", r.status_code == 200 and decision_id is not None)
    except Exception as e:
        check("decision recorded", False, str(e))

    if decision_id:
        try:
            r = httpx.patch(f"{BASE}/api/v1/autonomy/decisions/{decision_id}", params={"outcome": "verified"}, timeout=10)
            check("decision reviewed", r.json().get("outcome") == "verified")
        except Exception as e:
            check("decision reviewed", False, str(e))

    # 7. Authority enforcement — self-escalation rejected
    for action in ["grant_own_access", "modify_security_boundaries", "transfer_money"]:
        try:
            r = httpx.post(f"{BASE}/api/v1/governance/check-authority", json={
                "action_type": action, "requested_level": "1"
            }, timeout=10)
            check(f"authority blocks {action}", r.json().get("permitted") is False)
        except Exception as e:
            check(f"authority blocks {action}", False, str(e))

    # 8. Internet permission gates — exploration autonomous, consequential gated
    try:
        perms = httpx.get(f"{BASE}/api/v1/internet/permissions", timeout=10).json()
        pmap = {p["action_type"]: p for p in perms}
        check("browse is autonomous", pmap.get("browse_public", {}).get("is_autonomous") is True)
        check("spend is gated", pmap.get("spend_money", {}).get("requires_creator_authorization") is True)
    except Exception as e:
        check("internet permission gates", False, str(e))

    # 9. Permission check endpoint
    try:
        r = httpx.post(f"{BASE}/api/v1/internet/permissions/check", json={"action_type": "send_message"}, timeout=10)
        check("send_message requires authorization", r.json().get("permitted") is False)
    except Exception as e:
        check("permission check", False, str(e))

    # 10. Research workflow with provenance
    try:
        r = httpx.post(f"{BASE}/api/v1/research/", json={
            "query": "test research provenance", "store_as_memory": True, "max_results": 3
        }, timeout=30)
        d = r.json()
        check("research workflow executes", r.status_code == 200 and "query" in d)
        check("research preserves provenance", "sources" in d and isinstance(d.get("sources"), list))
    except Exception as e:
        check("research workflow", False, str(e))

    # 11. External AI network trust boundary
    try:
        r = httpx.post(f"{BASE}/api/v1/network/agents", json={
            "name": "L2 test agent", "endpoint_url": "https://example.invalid/api",
            "protocol": "rest", "capabilities": ["reasoning"]
        }, timeout=10)
        agent_id = r.json().get("id")
        check("agent registered as untrusted", r.status_code == 200 and agent_id is not None)
        if agent_id:
            agents = httpx.get(f"{BASE}/api/v1/network/agents", timeout=10).json()
            a = next((x for x in agents if x["id"] == agent_id), {})
            check("agent starts with zero trust", a.get("trust_score") == 0.0)
            check("agent not active until approved", a.get("is_active") is False)
    except Exception as e:
        check("AI network trust", False, str(e))

    # 12. Background autonomy worker
    try:
        s = httpx.get(f"{BASE}/api/v1/autonomy/status", timeout=10).json()
        check("autonomy worker running", s.get("running") is True)
    except Exception as e:
        check("autonomy worker", False, str(e))

    print("\n=== Level 2 summary ===")
    passed = sum(1 for r in results if r[1])
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
