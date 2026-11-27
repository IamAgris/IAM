"""Phase 8 tests: real reconciliation, P&L and separately authorised receipts."""

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from app.models.business import FinancialLedger, FinancialTransaction, IncomingReceipt
from app.models.security import AuditEvent
from app.services.ledger_service import LedgerError, LedgerService


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

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


def transaction(amount, tx_type, tx_id=None):
    return FinancialTransaction(
        id=tx_id or uuid.uuid4(),
        amount=amount,
        type=tx_type,
        created_at=datetime.now(timezone.utc),
    )


def approved(authorized=True):
    class Approvals:
        def __init__(self, _db):
            pass

        async def check_authorization(self, _action, requested_level="3", target_ref=None):
            if not authorized:
                return {"authorized": False, "reason": "unsigned"}
            return {
                "authorized": True,
                "authorization_id": str(uuid.uuid4()),
                "signer_id": "creator-signer",
            }

    return Approvals


class ReconciliationTests(unittest.IsolatedAsyncioTestCase):
    async def test_balanced_ledger_reconciles(self):
        tx = transaction(10, "income")
        db = FakeDB(
            [
                tx,
                FinancialLedger(
                    transaction_id=tx.id, account="bank", debit_amount=10, credit_amount=10
                ),
            ]
        )
        result = await LedgerService(db).reconcile()
        self.assertTrue(result["reconciled"])
        self.assertEqual(result["summary"]["difference"], 0.0)

    async def test_unbalanced_and_orphan_entries_detected(self):
        tx = transaction(10, "expense")
        db = FakeDB(
            [
                tx,
                FinancialLedger(
                    transaction_id=tx.id, account="bank", debit_amount=10, credit_amount=5
                ),
                FinancialLedger(
                    transaction_id=uuid.uuid4(), account="ghost", debit_amount=1, credit_amount=1
                ),
            ]
        )
        result = await LedgerService(db).reconcile()
        self.assertFalse(result["reconciled"])
        self.assertTrue(any("unbalanced" in issue for issue in result["issues"]))
        self.assertTrue(any("orphan" in issue for issue in result["issues"]))

    async def test_profit_and_loss(self):
        db = FakeDB([transaction(100, "income"), transaction(30, "expense")])
        result = await LedgerService(db).profit_and_loss()
        self.assertEqual(result["income"], 100.0)
        self.assertEqual(result["expenses"], 30.0)
        self.assertEqual(result["net"], 70.0)


class ReceiptTests(unittest.IsolatedAsyncioTestCase):
    async def test_receipt_requires_separate_authority(self):
        service = LedgerService(FakeDB())
        with self.assertRaises(LedgerError):
            await service.record_receipt(
                amount=10, source="client", reference="inv-1", approval_id=None, actor="iam"
            )
        with patch("app.services.ledger_service.CreatorApprovalService", approved(False)):
            with self.assertRaises(LedgerError):
                await service.record_receipt(
                    amount=10, source="client", reference="inv-1",
                    approval_id="fake", actor="iam",
                )

    async def test_receipt_recorded_without_spending_authority(self):
        db = FakeDB()
        with patch("app.services.ledger_service.CreatorApprovalService", approved()):
            result = await LedgerService(db).record_receipt(
                amount=25, source="client", reference="inv-1",
                approval_id="req-1", actor="iam",
            )
        self.assertFalse(result["spending_authority_granted"])
        self.assertTrue(any(isinstance(row, IncomingReceipt) for row in db.rows))
        self.assertTrue(
            any(
                row.event_type == "incoming_receipt_recorded"
                for row in db.rows
                if isinstance(row, AuditEvent)
            )
        )
        receipts = await LedgerService(db).receipts()
        self.assertEqual(receipts[0]["source"], "client")


if __name__ == "__main__":
    unittest.main()
