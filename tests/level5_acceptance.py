"""Level 5 — Ecosystem acceptance tests for IAM.

Run: python tests/level5_acceptance.py
Tests: opportunity discovery, project portfolio, double-entry ledger,
zero standing budget enforcement, budgets, external presence, ecosystem
integration isolation, life history.
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
    # 1. Opportunity discovery
    opp_id = None
    try:
        r = httpx.post(f"{BASE}/api/v1/economics/opportunities", json={
            "title": "L5 test opportunity", "estimated_revenue": 1000, "confidence": 0.7
        }, timeout=10)
        opp_id = r.json().get("id")
        check("opportunity discovered", r.status_code == 200 and opp_id is not None)
    except Exception as e:
        check("opportunity discovered", False, str(e))

    # 2. Business project
    proj_id = None
    try:
        r = httpx.post(f"{BASE}/api/v1/economics/projects", json={
            "name": "L5 test project", "opportunity_id": opp_id
        }, timeout=10)
        proj_id = r.json().get("id")
        check("business project created", r.status_code == 200 and proj_id is not None)
    except Exception as e:
        check("business project created", False, str(e))

    # 3. Zero standing budget — transaction without approval rejected
    try:
        r = httpx.post(f"{BASE}/api/v1/finance/transactions", json={
            "amount": 10, "type": "expense", "description": "unapproved"
        }, timeout=10)
        check("unapproved spend rejected", r.status_code == 403)
    except Exception as e:
        check("unapproved spend rejected", False, str(e))

    # 4. Approved transaction
    tx_id = None
    try:
        r = httpx.post(f"{BASE}/api/v1/finance/transactions", json={
            "amount": 10, "type": "income", "description": "approved test",
            "approval_id": "test-approval-001"
        }, timeout=10)
        tx_id = r.json().get("id")
        check("approved transaction recorded", r.status_code == 200 and tx_id is not None)
    except Exception as e:
        check("approved transaction", False, str(e))

    # 5. Double-entry ledger — unbalanced rejected
    if tx_id:
        try:
            r = httpx.post(f"{BASE}/api/v1/finance/ledger", json={
                "transaction_id": tx_id, "account": "test", "debit_amount": 10, "credit_amount": 5
            }, timeout=10)
            check("unbalanced ledger rejected", r.status_code == 400)
        except Exception as e:
            check("unbalanced ledger rejected", False, str(e))

        try:
            r = httpx.post(f"{BASE}/api/v1/finance/ledger", json={
                "transaction_id": tx_id, "account": "assets", "debit_amount": 10, "credit_amount": 10
            }, timeout=10)
            check("balanced ledger entry recorded", r.status_code == 200)
        except Exception as e:
            check("balanced ledger", False, str(e))

    # 6. Budget tracking
    try:
        r = httpx.post(f"{BASE}/api/v1/finance/budgets", json={
            "category": "infrastructure", "amount": 100, "period": "2026-11", "is_approved": False
        }, timeout=10)
        check("budget recorded (unapproved)", r.status_code == 200 and r.json().get("is_approved") is False)
    except Exception as e:
        check("budget", False, str(e))

    # 7. External presence registry (ecosystem integrations)
    # Unique name per run: repeated acceptance runs must not fail on a duplicate.
    try:
        import uuid
        integration_name = f"L5 test integration {uuid.uuid4().hex[:8]}"
        r = httpx.post(f"{BASE}/api/v1/external-presence/integrations", json={
            "name": integration_name, "provider": "test",
            "integration_type": "api",
            # No verified Creator email in a fresh dev stack, so skip the
            # approval email here. The registry must still create an inactive
            # integration that cannot be used before explicit activation.
            "requires_human_approval": False
        }, timeout=10)
        d = r.json()
        check("integration registered", r.status_code == 200 and d.get("id") is not None)
        check("integration inactive until approved", d.get("is_active") is False)
    except Exception as e:
        check("integration registry", False, str(e))

    # 8. Life history (chronological record)
    try:
        r = httpx.post(f"{BASE}/api/v1/life/history", json={
            "event_type": "milestone", "title": "L5 test milestone", "significance": 5
        }, timeout=10)
        check("life history recorded", r.status_code == 200)
    except Exception as e:
        check("life history", False, str(e))

    # 9. Multiple projects managed (portfolio)
    try:
        projects = httpx.get(f"{BASE}/api/v1/economics/projects", timeout=10).json()
        check("project portfolio available", isinstance(projects, list))
    except Exception as e:
        check("project portfolio", False, str(e))

    # 10. Ledger reconciliation view
    try:
        ledger = httpx.get(f"{BASE}/api/v1/finance/ledger", timeout=10).json()
        check("ledger queryable for reconciliation", isinstance(ledger, list))
    except Exception as e:
        check("ledger reconciliation", False, str(e))

    print("\n=== Level 5 summary ===")
    passed = sum(1 for r in results if r[1])
    print(f"{passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
