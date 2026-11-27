"""Tests for wallet verification, transaction operations and governance records.

SIWE verification is exercised with a real secp256k1 signature generated in-test.
No network call, signing key storage or value movement occurs.
"""

import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils

from app.core.config import settings
from app.services.blockchain.accounting import Web3AccountingService
from app.services.blockchain.business import Web3BusinessService
from app.services.blockchain.emergency import Web3EmergencyService
from app.services.blockchain.fiat import FiatRampResearch
from app.services.blockchain.keccak import keccak256
from app.services.blockchain.non_evm import NonEvmRegistry
from app.services.blockchain.providers.base import ProviderDenied
from app.services.blockchain.transaction_ops import (
    GasManager,
    NonceManager,
    StuckTransactionRecovery,
    TransactionQueue,
    TransactionSimulator,
)
from app.services.blockchain.wallet_ecosystem import (
    WalletEcosystemService,
    address_from_public_key,
    eip191_digest,
)
from app.services.blockchain.web3_learning import Web3LearningService


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
        self.rows.append(obj)

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


class KeccakTests(unittest.TestCase):
    def test_standard_vectors(self):
        self.assertEqual(
            keccak256(b"").hex(),
            "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470",
        )
        self.assertEqual(
            keccak256(b"abc").hex(),
            "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45",
        )


class SiweTests(unittest.TestCase):
    def test_real_signature_verifies_and_tampered_message_fails(self):
        key = ec.generate_private_key(ec.SECP256K1())
        numbers = key.public_key().public_numbers()
        address = address_from_public_key((numbers.x, numbers.y))
        message = (
            "example.com wants you to sign in with your Ethereum account:\n"
            f"{address}\n\nTest\n\nURI: https://example.com\nVersion: 1\nChain ID: 11155111\n"
            "Nonce: abc123\nIssued At: 2026-11-27T00:00:00Z"
        )
        digest = eip191_digest(message)
        der = key.sign(digest, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
        r, s = utils.decode_dss_signature(der)
        signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")

        service = WalletEcosystemService()
        with patch.object(settings, "web3_registry_enabled", True):
            verdict = None
            for recovery in (0, 1):
                result = service.verify_siwe(
                    message=message,
                    signature_hex=(signature + bytes([recovery])).hex(),
                    claimed_address=address,
                )
                if result["verified"]:
                    verdict = result
                    break
            self.assertIsNotNone(verdict)
            self.assertEqual(verdict["nonce"], "abc123")
            self.assertEqual(verdict["chain_id"], "11155111")
            tampered = service.verify_siwe(
                message=message + " ",
                signature_hex=(signature + bytes([1])).hex(),
                claimed_address=address,
            )
            self.assertFalse(tampered["verified"])

    def test_wallet_records_never_execute(self):
        with patch.object(settings, "web3_registry_enabled", True):
            service = WalletEcosystemService()
            result = service.session_key(
                wallet_id="W1", methods=["read_balance"], expiry="2027-01-01T00:00:00Z", spend_cap=5
            )
            self.assertFalse(result["execution_enabled"])
            self.assertFalse(result["can_create_session_keys"])
            multisig = service.multisig(wallet_id="W1", signers=["a", "b", "a"], threshold=2)
            self.assertEqual(multisig["signers"], ["a", "b"])
            transfer = service.prepare_transfer(
                wallet_id="W1", to_address="0x" + "1" * 40, amount=1, chain_id="11155111"
            )
            self.assertFalse(transfer["execution_enabled"])


class TransactionOpsTests(unittest.TestCase):
    def test_nonce_conflicts_and_replay_protection(self):
        manager = NonceManager()
        self.assertEqual(manager.next_nonce("1", "0xabc", 3), 3)
        self.assertEqual(manager.next_nonce("1", "0xabc"), 3)
        self.assertEqual(manager.conflicts("1", "0xabc", [1, 2, 5]), [1, 2])
        manager.mark_used("1", "0xabc", 3)
        with self.assertRaises(ProviderDenied):
            manager.mark_used("1", "0xabc", 2)

    def test_gas_budget_and_replacement(self):
        result = GasManager.estimate(
            base_fee=10, priority_fee=2, gas_units=100, budget_usd=5, price_usd=0.001
        )
        self.assertTrue(result["within_budget"])
        self.assertEqual(GasManager.replacement_fee(10), 11.0)

    def test_queue_idempotency_and_simulation_verdict(self):
        with patch.object(settings, "web3_transaction_preparation_enabled", True):
            queue = TransactionQueue()
            queue.enqueue("key-1", {"chain_id": "11155111"})
            with self.assertRaises(ProviderDenied):
                queue.enqueue("key-1", {})
            verdict = TransactionSimulator().simulate(
                chain_id="11155111", to_address="0xabc", amount=1,
                risk_flags=["unlimited_approval"],
            )
        self.assertEqual(verdict["verdict"], "deny")
        self.assertFalse(verdict["execution_enabled"])

    def test_stuck_recovery_never_auto_retries(self):
        result = StuckTransactionRecovery.assess(
            status="broadcast", has_tx_hash=False, age_minutes=60, threshold_minutes=30
        )
        self.assertTrue(result["stuck"])
        self.assertFalse(result["auto_retry"])


class RecordTests(unittest.IsolatedAsyncioTestCase):
    async def test_emergency_suspend_is_operator_only_and_audited(self):
        db = FakeDB()
        with patch.object(settings, "web3_registry_enabled", True):
            result = await Web3EmergencyService(db).suspend(reason="incident", actor="operator")
        self.assertTrue(result["suspended"])
        self.assertFalse(result["note"].find("IAM cannot lift") < 0)
        self.assertTrue(any(row.event_type == "web3_emergency_suspension" for row in db.rows))

    async def test_learning_cannot_promote_to_production(self):
        with patch.object(settings, "web3_registry_enabled", True):
            service = Web3LearningService()
            policy = service.policy()
            record = service.research_record(
                topic="ERC-4626", sources=["doc"], findings="notes", confidence=0.5
            )
            benchmark = service.benchmark(
                tool="t", baseline={"ms": 100}, candidate={"ms": 90}
            )
        self.assertFalse(policy["modifies_production_model"])
        self.assertTrue(record["promotion_requires_creator_approval"])
        self.assertFalse(benchmark["adopt"])


class AccountingResearchTests(unittest.TestCase):
    def test_fifo_basis_and_pnl(self):
        basis = Web3AccountingService.fifo_basis(
            lots=[{"date": "1", "quantity": 2, "unit_cost": 10}, {"date": "2", "quantity": 1, "unit_cost": 12}],
            quantity=2,
        )
        self.assertEqual(basis["cost_basis"], 20)
        pnl = Web3AccountingService.realised_pnl(proceeds=30, cost_basis=20, fees=1)
        self.assertEqual(pnl["realised_pnl"], 9)

    def test_business_and_fiat_research_fail_closed(self):
        with patch.object(settings, "web3_registry_enabled", True):
            business = Web3BusinessService().evaluate(
                category="web3_saas", estimated_cost_usd=10, demand_evidence=[], competition=[]
            )
            eligible = FiatRampResearch().evaluate(
                provider="p", fee_pct=1, supports_south_africa=True,
                kyc_required=True, terms_verified=True,
            )
            networks = NonEvmRegistry().list("zk_rollup")
        self.assertEqual(business["recommendation"], "do_not_proceed")
        self.assertTrue(eligible["eligible"])
        self.assertTrue(all(not item["verified"] for item in networks))


if __name__ == "__main__":
    unittest.main()
