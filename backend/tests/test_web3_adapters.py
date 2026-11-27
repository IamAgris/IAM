"""Proposed Doc 30 tests — read-only adapters, registries and prepare-only transactions.

No test in this module performs a network call, signs, broadcasts or pays.
"""

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.config import settings
from app.models.security import AuditEvent, SecurityIncident
from app.models.web3 import BlockchainAuditLog, Web3Transaction
from app.services.blockchain.activation import check_web3_activation
from app.services.blockchain.audit import BlockchainAuditService
from app.services.blockchain.governance import ExecutionAuthorization, Web3ApprovalService
from app.services.blockchain.monitoring import Web3MonitoringService
from app.services.blockchain.network_registry import NetworkRegistry
from app.services.blockchain.node_service import NodeService
from app.services.blockchain.providers.base import ProviderDenied
from app.services.blockchain.providers.bitcoin_core_adapter import BitcoinCoreAdapter
from app.services.blockchain.providers.cln_adapter import ClnAdapter
from app.services.blockchain.providers.lnd_adapter import LndAdapter
from app.services.blockchain.providers.thirdweb_adapter import ThirdwebReadAdapter
from app.services.blockchain.transaction_manager import TransactionManager
from app.services.blockchain.wallet_registry import WalletRegistry
from app.services.financial_policy import SpendDenied


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


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


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_thirdweb_defaults_off_and_paid_feature_denied(self):
        adapter = ThirdwebReadAdapter()
        with patch.object(settings, "thirdweb_read_enabled", False):
            with self.assertRaises(ProviderDenied):
                await adapter.get_balance("0xabc")
        with patch.object(settings, "thirdweb_read_enabled", True), patch.object(
            settings, "thirdweb_base_url", "https://rpc.example"
        ):
            with patch(
                "app.services.blockchain.providers.thirdweb_adapter.read_secret",
                return_value="client-id",
            ):
                with self.assertRaises(ProviderDenied):
                    await adapter._rpc("paid_rpc_capacity", [])

    async def test_thirdweb_build_is_prepared_without_network(self):
        with patch.object(settings, "web3_transaction_preparation_enabled", True):
            result = await ThirdwebReadAdapter().build_transaction(
                {"chain_id": "11155111", "to_address": "0xabc", "amount": 2}
            )
        self.assertEqual(result.data["status"], "prepared")
        self.assertTrue(result.data["approval_required"])
        self.assertFalse(result.data["execution_enabled"])
        self.assertFalse(result.network_calls_made)

    async def test_thirdweb_broadcast_denied(self):
        with self.assertRaises(ProviderDenied):
            await ThirdwebReadAdapter().broadcast({})

    async def test_bitcoin_read_allowlist_and_no_broadcast(self):
        adapter = BitcoinCoreAdapter()
        self.assertNotIn("sendtoaddress", adapter.policy()["allowed_methods"])
        self.assertNotIn("sendrawtransaction", adapter.policy()["allowed_methods"])
        with patch.object(settings, "bitcoin_core_read_enabled", True):
            with self.assertRaises(ProviderDenied):
                await adapter._rpc("sendtoaddress", ["addr", 1])
        with self.assertRaises(ProviderDenied):
            await adapter.broadcast({})

    async def test_lnd_and_cln_execution_denied(self):
        for adapter in (LndAdapter(), ClnAdapter()):
            with self.assertRaises(ProviderDenied):
                await adapter.create_invoice({})
            with self.assertRaises(ProviderDenied):
                await adapter.pay_invoice({})
        self.assertNotIn("payinvoice", ClnAdapter().policy()["allowed_methods"])
        self.assertNotIn("/v1/channels/transactions", LndAdapter().policy()["allowed_paths"])

    async def test_lnd_cln_tls_never_disabled(self):
        with patch.object(settings, "lnd_tls_cert_env", "MISSING_CERT"):
            with patch(
                "app.services.blockchain.providers.lnd_adapter.read_secret",
                return_value=None,
            ):
                with self.assertRaises(ProviderDenied):
                    LndAdapter()._tls()


class RegistryTests(unittest.IsolatedAsyncioTestCase):
    def test_network_capability_fails_closed(self):
        registry = NetworkRegistry()
        self.assertTrue(registry.capability("11155111", "prepare_transaction")["allowed"])
        self.assertFalse(registry.capability("1", "broadcast")["allowed"])
        self.assertTrue(registry.get_network("1")["production_gated"])
        with self.assertRaises(ProviderDenied):
            registry.get_network("999999")

    async def test_wallet_registry_has_no_key_fields_and_enforces_transitions(self):
        db = FakeDB()
        registry = WalletRegistry(db)
        with patch.object(settings, "web3_registry_enabled", True):
            wallet = await registry.register(
                domain="operational", provider="thirdweb", address="0xabc", actor="test"
            )
            self.assertEqual(wallet["state"], "proposed")
            with self.assertRaises(ProviderDenied):
                await registry.transition(wallet_id=wallet["wallet_id"], target="active")
            verified = await registry.transition(
                wallet_id=wallet["wallet_id"],
                target="verified",
                verification_method="siwe",
                verification_evidence_ref="evidence-1",
            )
            self.assertEqual(verified["state"], "verified")
        row = db.rows[0]
        self.assertFalse(any("key" in column.lower() for column in vars(row)))
        self.assertFalse(registry.policy()["address_grants_authority"])

    async def test_prepare_is_idempotent_and_never_broadcasts(self):
        db = FakeDB()
        manager = TransactionManager(db)
        payload = {"chain_id": "11155111", "to_address": "0xabc", "amount": 3}
        with patch.object(settings, "web3_transaction_preparation_enabled", True):
            first = await manager.prepare(payload)
            second = await manager.prepare(payload)
            self.assertEqual(first["status"], "simulated")
            self.assertFalse(first["execution_enabled"])
            self.assertEqual(second["duplicate_of"], first["id"])
            self.assertEqual(len([r for r in db.rows if isinstance(r, Web3Transaction)]), 1)

    async def test_broadcast_denied_without_execution_flag(self):
        with patch.object(settings, "web3_execution_enabled", False):
            with self.assertRaises(ProviderDenied):
                await TransactionManager(FakeDB()).broadcast("anything")


class AuditTests(unittest.IsolatedAsyncioTestCase):
    async def test_hash_chain_detects_tampering_and_redacts_secrets(self):
        db = FakeDB()
        service = BlockchainAuditService(db)
        with patch.object(settings, "web3_audit_enabled", True):
            first = await service.append(
                event_type="web3_transaction_prepared",
                actor="test",
                target="tx-1",
                details={"secret_key": "must-not-appear", "chain_id": "11155111"},
            )
            second = await service.append(
                event_type="web3_wallet_registered", actor="test", target="wallet-1"
            )
        self.assertEqual(first["prev_hash"], "0" * 64)
        self.assertEqual(second["prev_hash"], first["entry_hash"])
        good = await service.verify()
        self.assertTrue(good["verified"])
        stored = [row for row in db.rows if isinstance(row, BlockchainAuditLog)][0]
        self.assertEqual(stored.details["secret_key"], "[redacted]")
        stored.entry_hash = "tampered"
        bad = await service.verify()
        self.assertFalse(bad["verified"])
        self.assertTrue(any("hash mismatch" in issue for issue in bad["issues"]))

    async def test_audit_disabled_by_default(self):
        with patch.object(settings, "web3_audit_enabled", False):
            with self.assertRaises(ProviderDenied):
                await BlockchainAuditService(FakeDB()).append(
                    event_type="test", actor="test"
                )


def approvals(authorized=True):
    class Approvals:
        def __init__(self, _db):
            pass

        async def create_request(self, **kwargs):
            return {
                "request_id": "cr_test",
                "challenge_hash": "hash",
                "status": "pending",
                "action_type": kwargs["action_type"],
            }

        async def check_authorization(self, _action, requested_level="3", target_ref=None):
            if not authorized:
                return {"authorized": False, "reason": "unsigned"}
            return {
                "authorized": True,
                "authorization_id": "auth-1",
                "signer_id": "creator-signer",
                "expires_at": "2030-01-01T00:00:00+00:00",
            }

    return Approvals


class ApprovalTests(unittest.IsolatedAsyncioTestCase):
    async def test_authorize_denies_without_signed_approval(self):
        with patch(
            "app.services.blockchain.governance.CreatorApprovalService", approvals(False)
        ):
            with self.assertRaises(ProviderDenied):
                await Web3ApprovalService(FakeDB()).authorize(
                    action="web3.transaction.broadcast", approval_id="cr_fake",
                    amount_usd=5,
                )

    async def test_spend_requires_usd_valuation_and_od04_caps(self):
        with patch("app.services.blockchain.governance.CreatorApprovalService", approvals()):
            service = Web3ApprovalService(FakeDB())
            with self.assertRaises(ProviderDenied):
                await service.authorize(
                    action="web3.transaction.broadcast", approval_id="cr_1"
                )
            with patch(
                "app.services.blockchain.governance.authorize_transaction",
                side_effect=SpendDenied("cap exceeded"),
            ):
                with self.assertRaises(ProviderDenied):
                    await service.authorize(
                        action="web3.transaction.broadcast", approval_id="cr_1",
                        amount_usd=50,
                    )

    async def test_authorization_proof_is_emitted_after_verification(self):
        with patch("app.services.blockchain.governance.CreatorApprovalService", approvals()), patch(
            "app.services.blockchain.governance.authorize_transaction"
        ):
            proof = await Web3ApprovalService(FakeDB()).authorize(
                action="web3.invoice.create", approval_id="cr_1"
            )
        self.assertTrue(proof.verified)
        self.assertEqual(proof.level, "2")
        self.assertNotIn("secret", proof.summary())

    async def test_protected_action_requires_level_four(self):
        proof = ExecutionAuthorization(
            action="web3.treasury.withdraw", approval_id="cr_1",
            authorization_id="auth-1", level="3", amount_usd=5,
            expires_at=None,
        )
        with self.assertRaises(ProviderDenied):
            Web3ApprovalService.require_protected(proof)

    async def test_full_prepare_request_confirm_flow(self):
        db = FakeDB()
        manager = TransactionManager(db)
        with patch.object(settings, "web3_transaction_preparation_enabled", True), patch(
            "app.services.blockchain.governance.CreatorApprovalService", approvals()
        ):
            prepared = await manager.prepare(
                {"chain_id": "11155111", "to_address": "0xabc", "amount": 2}
            )
            requested = await manager.request_approval(prepared["id"])
            self.assertEqual(requested["status"], "awaiting_approval")
            self.assertFalse(requested["plain_reply_authorises"])
            with patch("app.services.blockchain.governance.authorize_transaction"):
                confirmed = await manager.confirm_approval(prepared["id"], "cr_test", 5)
            self.assertEqual(confirmed["status"], "approved")
            self.assertFalse(confirmed["broadcast"])
            with patch.object(settings, "web3_execution_enabled", False):
                with self.assertRaises(ProviderDenied):
                    await manager.broadcast(prepared["id"], 5)

    async def test_execution_denied_without_configured_signer(self):
        db = FakeDB()
        manager = TransactionManager(db)
        with patch.object(settings, "web3_transaction_preparation_enabled", True), patch(
            "app.services.blockchain.governance.CreatorApprovalService", approvals()
        ), patch("app.services.blockchain.governance.authorize_transaction"):
            prepared = await manager.prepare(
                {"chain_id": "11155111", "to_address": "0xabc", "amount": 2}
            )
            await manager.request_approval(prepared["id"])
            await manager.confirm_approval(prepared["id"], "cr_test", 5)
            with patch.object(settings, "web3_execution_enabled", True), patch.object(
                settings, "web3_executor_url", ""
            ):
                with self.assertRaises(ProviderDenied):
                    await manager.broadcast(prepared["id"], 5)


class ActivationTests(unittest.TestCase):
    def test_all_flags_off_is_ready(self):
        result = check_web3_activation()
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], [])
        self.assertTrue(
            any(item["name"] == "web3_flags_default_off" for item in result["checks"])
        )

    def test_execution_blocked_without_decision_evidence_and_executor(self):
        with patch.object(settings, "web3_execution_enabled", True):
            result = check_web3_activation()
        self.assertFalse(result["ready"])
        for name in (
            "web3_owner_decision",
            "web3_testnet_evidence",
            "web3_executor",
        ):
            self.assertIn(name, result["blockers"])

    def test_report_never_contains_secret_values(self):
        import os

        os.environ["THIRDWEB_SECRET_KEY"] = "IAM_TEST_SENTINEL_123"
        try:
            with patch.object(settings, "web3_execution_enabled", True):
                result = check_web3_activation()
            self.assertNotIn("IAM_TEST_SENTINEL_123", str(result))
        finally:
            os.environ.pop("THIRDWEB_SECRET_KEY", None)


class MonitoringTests(unittest.IsolatedAsyncioTestCase):
    async def test_monitoring_disabled_by_default(self):
        with patch.object(settings, "web3_monitoring_enabled", False):
            with self.assertRaises(ProviderDenied):
                await Web3MonitoringService(FakeDB()).run_checks()

    async def test_stuck_broadcast_creates_high_severity_alert(self):
        db = FakeDB()
        db.add(
            Web3Transaction(
                chain_id="11155111",
                to_address="0xabc",
                amount=1,
                status="broadcast",
                idempotency_key="key-1",
                tx_hash=None,
                created_at=datetime.now(timezone.utc) - timedelta(minutes=60),
            )
        )
        with patch.object(settings, "web3_monitoring_enabled", True):
            result = await Web3MonitoringService(db).run_checks()
        self.assertFalse(result["network_calls_made"])
        self.assertTrue(any(alert["severity"] == "high" for alert in result["alerts"]))
        self.assertTrue(any(isinstance(row, SecurityIncident) for row in db.rows))
        self.assertTrue(any(row.event_type == "web3_alert" for row in db.rows if isinstance(row, AuditEvent)))


class NodeTests(unittest.IsolatedAsyncioTestCase):
    async def test_comparison_keeps_nodes_independent_when_disabled(self):
        with patch.object(settings, "lnd_read_enabled", False), patch.object(
            settings, "cln_read_enabled", False
        ):
            result = await NodeService().compare()
        self.assertEqual(result["candidates"], [])
        self.assertFalse(result["identities_merged"])
        self.assertFalse(result["auto_routing_enabled"])

    async def test_node_adapters_report_no_network_calls(self):
        service = NodeService()
        health = await service.health()
        self.assertFalse(health["network_calls_made"])


if __name__ == "__main__":
    unittest.main()
