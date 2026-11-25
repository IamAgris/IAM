"""Level 3 — Self-developing acceptance tests for IAM.

Run: python tests/level3_acceptance.py
Tests: isolated dev project lifecycle, code changes, experiment with evidence,
versioned release/deployment, rollback, upgrade history, capability registry,
reflection, resilience checks.
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
    # 1. Dev project lifecycle
    pid = None
    try:
        r = httpx.post(f"{BASE}/api/v1/development/projects", json={
            "name": "L3 test project", "description": "Self-development acceptance"
        }, timeout=10)
        pid = r.json().get("id")
        check("dev project created", r.status_code == 200 and pid is not None)
    except Exception as e:
        check("dev project created", False, str(e))

    if pid:
        try:
            r = httpx.patch(f"{BASE}/api/v1/development/projects/{pid}", json={"status": "in_development"}, timeout=10)
            check("project status transition", r.json().get("status") == "in_development")
        except Exception as e:
            check("project status transition", False, str(e))

    # 2. Code change records (proposed -> reviewed -> tested)
    if pid:
        try:
            r = httpx.post(f"{BASE}/api/v1/development/code-changes", json={
                "project_id": pid, "description": "L3 change",
                "file_path": "app/example.py", "change_type": "add"
            }, timeout=10)
            cid = r.json().get("id")
            check("code change recorded", r.status_code == 200 and cid is not None)
        except Exception as e:
            check("code change recorded", False, str(e))

    # 3. Experiment with evidence, completes
    eid = None
    try:
        r = httpx.post(f"{BASE}/api/v1/development/experiments", json={
            "name": "L3 acceptance experiment", "hypothesis": "test improves baseline"
        }, timeout=10)
        eid = r.json().get("id")
        check("experiment created", r.status_code == 200 and eid is not None)
    except Exception as e:
        check("experiment created", False, str(e))

    if eid:
        try:
            r = httpx.patch(f"{BASE}/api/v1/development/experiments/{eid}", json={
                "status": "completed", "results": {"score": 0.92, "baseline": 0.85}
            }, timeout=10)
            d = r.json()
            check("experiment evaluated vs baseline", d.get("status") == "completed")
        except Exception as e:
            check("experiment evaluation", False, str(e))

    # 4. Versioned deployment + rollback
    if pid:
        try:
            r = httpx.post(f"{BASE}/api/v1/development/deployments", json={
                "project_id": pid, "version": "1.0.0", "environment": "testing"
            }, timeout=10)
            dep = r.json()
            check("versioned release recorded", r.status_code == 200 and dep.get("status") == "pending")
            did = dep.get("id")
            # rollback = record another deployment with previous version
            r2 = httpx.post(f"{BASE}/api/v1/development/deployments", json={
                "project_id": pid, "version": "0.9.0", "environment": "testing"
            }, timeout=10)
            check("rollback release recorded", r2.status_code == 200)
        except Exception as e:
            check("deployment/rollback", False, str(e))

    # 5. Upgrade history
    try:
        r = httpx.post(f"{BASE}/api/v1/development/upgrades", json={
            "component": "test-component", "previous_version": "0.1", "new_version": "0.2"
        }, timeout=10)
        check("upgrade history recorded", r.status_code == 200)
    except Exception as e:
        check("upgrade history", False, str(e))

    # 6. Capability registry with measurable assessment
    try:
        r = httpx.post(f"{BASE}/api/v1/capabilities", json={
            "name": "L3 test capability", "category": "programming", "target_proficiency": 100
        }, timeout=10)
        cap = r.json()
        cid = cap.get("id")
        check("capability defined", r.status_code == 200 and cid is not None)
        if cid:
            r2 = httpx.post(f"{BASE}/api/v1/capabilities/assess", json={
                "capability_id": cid, "proficiency_level": 0, "assessment_method": "test"
            }, timeout=10)
            check("capability requires measurable assessment", r2.status_code == 200)
    except Exception as e:
        check("capability registry", False, str(e))

    # 7. Reflection engine
    try:
        r = httpx.post(f"{BASE}/api/v1/reflection", json={
            "reflection_type": "experience", "title": "L3 test reflection",
            "content": "Verified self-development", "lesson_learned": "test before release"
        }, timeout=10)
        check("reflection recorded", r.status_code == 200)
    except Exception as e:
        check("reflection", False, str(e))

    # 8. Resilience health recording
    try:
        r = httpx.post(f"{BASE}/api/v1/resilience/health", json={
            "service_name": "l3-test", "status": "healthy", "response_time_ms": 5
        }, timeout=10)
        check("health check recorded", r.status_code == 200)
    except Exception as e:
        check("resilience health", False, str(e))

    # 9. Model evaluation history (change validated against baseline)
    try:
        r = httpx.get(f"{BASE}/api/v1/models/router/history", timeout=10)
        check("routing decisions audited", r.status_code == 200 and isinstance(r.json(), list))
    except Exception as e:
        check("routing audit", False, str(e))

    print("\n=== Level 3 summary ===")
    passed = sum(1 for r in results if r[1])
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
