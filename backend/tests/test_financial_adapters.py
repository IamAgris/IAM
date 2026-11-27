"""Phase 8 adapter tests: free-only blockchain, gated banking, paper trading."""

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from app.core.config import settings
from app.models.security import AuditEvent
from app.services.banking.service import BankingDenied, BankingService, BANKING_CAPABILITIES
from app.services.blockchain.service import BlockchainDenied, BlockchainService
from app.services.trading.paper import PaperTradingService, TradingDenied


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
    def __init__(self):
        self.rows = []

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


def approvals(authorized=True):
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


class BlockchainTests(unittest.IsolatedAsyncioTestCase):
    async def test_policy_is_free_only_and_testnet(self):
        with patch.object(settings, "blockchain_enabled", False):
            policy = BlockchainService(FakeDB()).policy()
        self.assertTrue(policy["free_only"])
        self.assertFalse(policy["paid_plans_allowed"])
        self.assertIn(policy["testnet_chain_id"], policy["allowed_testnets"])

    async def test_write_requires_enablement_and_signed_authority(self):
        service = BlockchainService(FakeDB())
        with patch.object(settings, "blockchain_enabled", False):
            with self.assertRaises(BlockchainDenied):
                await service.record_activity(
                    asset="USDC", amount=1, address="0xabc", tx_hash="", approval_id="r1", actor="iam"
                )
        with patch.object(settings, "blockchain_enabled", True), patch(
            "app.services.blockchain.service.CreatorApprovalService", approvals(False)
        ):
            with self.assertRaises(BlockchainDenied):
                await service.record_activity(
                    asset="USDC", amount=1, address="0xabc", tx_hash="", approval_id="r1", actor="iam"
                )

    async def test_signed_activity_recorded_without_network_call(self):
        db = FakeDB()
        with patch.object(settings, "blockchain_enabled", True), patch(
            "app.services.blockchain.service.CreatorApprovalService", approvals()
        ):
            result = await BlockchainService(db).record_activity(
                asset="USDC", amount=2, address="0xabc", tx_hash="0xhash",
                approval_id="r1", actor="iam",
            )
        self.assertFalse(result["network_calls_made"])
        self.assertTrue(any(row.event_type == "blockchain_activity_recorded" for row in db.rows if isinstance(row, AuditEvent)))


class BankingTests(unittest.IsolatedAsyncioTestCase):
    def test_eighteen_capabilities_declared(self):
        self.assertEqual(len(BANKING_CAPABILITIES), 18)

    async def test_consent_and_payment_gates(self):
        db = FakeDB()
        service = BankingService(db)
        with patch.object(settings, "banking_enabled", True), patch(
            "app.services.banking.service.CreatorApprovalService", approvals()
        ):
            consent = await service.request_consent(
                institution="Test Bank", account_ref="acct-1",
                capabilities=["payment_initiation", "account_balance"],
                approval_id="r1", ttl_seconds=3600, actor="iam",
            )
            with patch("app.services.banking.service.CreatorApprovalService", approvals(False)):
                with self.assertRaises(BankingDenied):
                    await service.propose_payment(
                        consent_id=consent["id"], amount=50,
                        beneficiary="supplier", approval_id="fake", actor="iam",
                    )
            payment = await service.propose_payment(
                consent_id=consent["id"], amount=50,
                beneficiary="supplier", approval_id="r2", actor="iam",
            )
        self.assertFalse(payment["submitted"])
        revoked = await service.revoke_consent(consent["id"], "iam")
        self.assertFalse(revoked["is_active"])

    async def test_unknown_capability_denied(self):
        with patch.object(settings, "banking_enabled", True):
            with self.assertRaises(BankingDenied):
                await BankingService(FakeDB()).request_consent(
                    institution="Bank", account_ref="a",
                    capabilities=["unknown_capability"], approval_id="r1",
                    ttl_seconds=60, actor="iam",
                )


class TradingTests(unittest.IsolatedAsyncioTestCase):
    async def test_order_limits_and_emergency_stop(self):
        db = FakeDB()
        service = PaperTradingService(db)
        with patch.object(settings, "trading_simulation_enabled", True):
            portfolio = await service.create_portfolio("demo", 1000, "iam")
            self.assertTrue(portfolio["simulation_only"])
            order = await service.place_order(
                portfolio["id"], symbol="ABC", side="buy",
                quantity=2, price=3, actor="iam",
            )
            self.assertEqual(order["status"], "simulated")
            with self.assertRaises(TradingDenied):
                await service.place_order(
                    portfolio["id"], symbol="ABC", side="buy",
                    quantity=100, price=3, actor="iam",
                )
            with patch("app.services.trading.paper.CreatorApprovalService", approvals()):
                stopped = await service.emergency_stop(portfolio["id"], True, "iam")
            self.assertTrue(stopped["emergency_stop"])
            with self.assertRaises(TradingDenied):
                await service.place_order(
                    portfolio["id"], symbol="ABC", side="buy",
                    quantity=1, price=1, actor="iam",
                )
            report = await service.report(portfolio["id"])
            self.assertEqual(report["orders"], 1)
            self.assertTrue(any(row.event_type == "paper_order_simulated" for row in db.rows if isinstance(row, AuditEvent)))

    async def test_limits_require_signed_authority(self):
        db = FakeDB()
        service = PaperTradingService(db)
        with patch.object(settings, "trading_simulation_enabled", True):
            portfolio = await service.create_portfolio("demo", 100, "iam")
            with patch("app.services.trading.paper.CreatorApprovalService", approvals(False)):
                with self.assertRaises(TradingDenied):
                    await service.set_limits(
                        portfolio["id"], {"max_order_usd": 5}, "iam"
                    )
            with patch("app.services.trading.paper.CreatorApprovalService", approvals()):
                updated = await service.set_limits(
                    portfolio["id"], {"max_order_usd": 5}, "iam"
                )
            self.assertEqual(updated["risk_limits"]["max_order_usd"], 5.0)


if __name__ == "__main__":
    unittest.main()
