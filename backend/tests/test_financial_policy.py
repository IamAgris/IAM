"""OD-04 tests: signed per-action spend authority and hard caps."""

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from app.api.routes.economy import (
    BudgetCreate,
    TransactionCreate,
    create_budget,
    create_transaction,
)
from app.core.config import settings
from app.models.business import FinancialTransaction
from app.models.security import AuditEvent
from app.services.financial_policy import (
    SPEND_ACTION,
    TRANSFER_ACTION,
    SpendDenied,
    authorize_transaction,
)


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def add(self, obj):
        if obj not in self.rows:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.rows.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


def approvals(authorized=True):
    class Approvals:
        def __init__(self, _db):
            pass

        async def check_authorization(self, action, requested_level="3", target_ref=None):
            calls.append((action, requested_level, target_ref))
            if not authorized:
                return {"authorized": False, "reason": "unsigned"}
            return {
                "authorized": True,
                "authorization_id": str(uuid.uuid4()),
                "signer_id": "creator-signer",
                "target_ref": target_ref,
            }

    calls = []
    return Approvals, calls


def fake_request():
    state = type("State", (), {"credential": {"name": "iam"}})()
    return type("Request", (), {"state": state})()


class PolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_income_is_autonomous(self):
        with patch("app.services.financial_policy.CreatorApprovalService", approvals()[0]):
            result = await authorize_transaction(
                FakeDB(), amount=50, transaction_type="income", approval_id=None
            )
        self.assertIsNone(result)

    async def test_missing_or_unknown_approval_denied(self):
        with patch(
            "app.services.financial_policy.CreatorApprovalService", approvals(False)[0]
        ):
            with self.assertRaises(SpendDenied):
                await authorize_transaction(
                    FakeDB(), amount=5, transaction_type="expense", approval_id=None
                )
            with self.assertRaises(SpendDenied):
                await authorize_transaction(
                    FakeDB(), amount=5, transaction_type="expense", approval_id="unknown"
                )

    async def test_transfer_uses_level_four_action(self):
        Approvals, calls = approvals()
        with patch("app.services.financial_policy.CreatorApprovalService", Approvals):
            result = await authorize_transaction(
                FakeDB(), amount=5, transaction_type="transfer", approval_id="req-1"
            )
        self.assertTrue(result["authorized"])
        self.assertEqual(calls[0], (TRANSFER_ACTION, "4", "req-1"))

    async def test_transaction_cap_is_configurable_within_od04_band(self):
        with patch.object(settings, "finance_transaction_limit_usd", 5.0), patch(
            "app.services.financial_policy.CreatorApprovalService", approvals()[0]
        ):
            result = await authorize_transaction(
                FakeDB(), amount=5, transaction_type="expense", approval_id="req-1"
            )
            self.assertTrue(result["authorized"])
            with self.assertRaises(SpendDenied):
                await authorize_transaction(
                    FakeDB(), amount=6, transaction_type="expense", approval_id="req-1"
                )

    async def test_out_of_band_config_is_clamped(self):
        with patch.object(settings, "finance_transaction_limit_usd", 50.0):
            with patch("app.services.financial_policy.CreatorApprovalService", approvals()[0]):
                with self.assertRaises(SpendDenied):
                    await authorize_transaction(
                        FakeDB(), amount=11, transaction_type="expense", approval_id="req-1"
                    )

    async def test_monthly_cap(self):
        existing = FinancialTransaction(
            amount=95.0,
            type="expense",
            created_at=datetime.now(timezone.utc),
        )
        with patch.object(settings, "finance_monthly_limit_usd", 100.0), patch(
            "app.services.financial_policy.CreatorApprovalService", approvals()[0]
        ):
            with self.assertRaises(SpendDenied):
                await authorize_transaction(
                    FakeDB([existing]),
                    amount=10,
                    transaction_type="expense",
                    approval_id="req-1",
                )


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_budget_cannot_self_approve(self):
        db = FakeDB()
        result = await create_budget(
            BudgetCreate(category="ops", amount=50, period="monthly", is_approved=True),
            fake_request(),
            db,
        )
        self.assertFalse(result["is_approved"])
        self.assertTrue(
            any(row.event_type == "finance_budget_proposed" for row in db.rows if isinstance(row, AuditEvent))
        )

    async def test_transaction_persists_signed_authority(self):
        db = FakeDB()
        authorization_id = str(uuid.uuid4())

        class Approvals:
            def __init__(self, _db):
                pass

            async def check_authorization(self, _action, requested_level="3", target_ref=None):
                return {
                    "authorized": True,
                    "authorization_id": authorization_id,
                    "signer_id": "creator-signer",
                }

        with patch("app.services.financial_policy.CreatorApprovalService", Approvals):
            result = await create_transaction(
                TransactionCreate(amount=5, type="expense", approval_id="req-1"),
                fake_request(),
                db,
            )
        self.assertTrue(result["signed_authority"])
        stored = next(row for row in db.rows if isinstance(row, FinancialTransaction))
        self.assertEqual(stored.reference_id, authorization_id)
        self.assertTrue(
            any(
                row.event_type == "financial_transaction_recorded"
                for row in db.rows
                if isinstance(row, AuditEvent)
            )
        )


if __name__ == "__main__":
    unittest.main()
