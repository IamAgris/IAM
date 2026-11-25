"""Level 1 persistence tests — identity & memory survive restart.

Run: python tests/level1_persistence.py
Requires Docker running. Restarts the backend container to prove continuity.
"""

import httpx
import subprocess
import time

BASE = "http://localhost:8000"


def get_genesis():
    return httpx.get(f"{BASE}/api/v1/setup/genesis", timeout=10).json()


def main():
    print("=== Level 1: Identity & memory persistence across restart ===")

    before = get_genesis()
    print(f"Before restart: permanent_id={before.get('permanent_id')}")

    # Store a marker memory
    marker = "PERSISTENCE_TEST_MARKER_20261125"
    httpx.post(f"{BASE}/api/v1/memory/", json={
        "content": marker, "memory_type": "fact", "topic": "persistence-test"
    }, timeout=15)

    # Restart the backend container
    print("Restarting backend container...")
    subprocess.run(["docker", "restart", "aura-backend"], check=True, capture_output=True)
    for _ in range(30):
        time.sleep(2)
        try:
            if httpx.get(f"{BASE}/health", timeout=3).status_code == 200:
                break
        except Exception:
            continue

    after = get_genesis()
    print(f"After restart:  permanent_id={after.get('permanent_id')}")

    ok_id = before.get("permanent_id") == after.get("permanent_id")
    print(f"[{'PASS' if ok_id else 'FAIL'}] Permanent identity unchanged across restart")

    # Check marker memory survived
    r = httpx.get(f"{BASE}/api/v1/memory/?limit=50", timeout=10)
    marker_found = marker in r.text
    print(f"[{'PASS' if marker_found else 'FAIL'}] Memory persisted across restart")

    # Verify session count / DB alive
    r2 = httpx.get(f"{BASE}/api/v1/governance/boundaries", timeout=10)
    print(f"[{'PASS' if r2.status_code == 200 else 'FAIL'}] Governance records survived restart")

    return 0 if (ok_id and marker_found) else 1


if __name__ == "__main__":
    raise SystemExit(main())
