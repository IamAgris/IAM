"""Proposed Doc 33 tests — extended Web3 research and preparation modules.

No test performs a network call, signs, mints, swaps, bridges or votes.
"""

import unittest
from unittest.mock import patch

from app.core.config import settings
from app.services.blockchain.contracts import ContractIntelligenceService
from app.services.blockchain.cross_chain import CrossChainService
from app.services.blockchain.dao import DaoGovernanceService
from app.services.blockchain.defi import DeFiIntelligenceService
from app.services.blockchain.nft import DigitalAssetService
from app.services.blockchain.onchain_analysis import OnChainAnalysisService
from app.services.blockchain.providers.base import ProviderDenied
from app.services.blockchain.threat_intel import ThreatIntelService
from app.services.blockchain.x402 import X402Service


class DeFiTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with self.assertRaises(ProviderDenied):
            DeFiIntelligenceService().compare_swaps([])

    def test_unverified_quotes_rank_last(self):
        quotes = [
            {"protocol": "risky", "chain_id": "1", "token_in": "A", "token_out": "B",
             "amount_in": 1, "amount_out": 999, "verified": False},
            {"protocol": "checked", "chain_id": "1", "token_in": "A", "token_out": "B",
             "amount_in": 1, "amount_out": 90, "verified": True},
        ]
        with patch.object(settings, "web3_defi_enabled", True):
            result = DeFiIntelligenceService().compare_swaps(quotes)
        self.assertEqual(result["best"]["protocol"], "checked")
        self.assertFalse(result["execution_enabled"])

    def test_impermanent_loss_at_same_price_is_zero(self):
        self.assertEqual(DeFiIntelligenceService.impermanent_loss(1)["impermanent_loss"], 0)

    def test_liquidation_and_staking_are_estimates(self):
        risk = DeFiIntelligenceService.liquidation_risk(
            collateral_usd=100, debt_usd=90, threshold=0.8, price_drop_pct=30
        )
        self.assertEqual(risk["liquidation_risk"], "high")
        reward = DeFiIntelligenceService.staking_estimate(amount=100, apy_pct=10, days=365)
        self.assertIn("not a return guarantee", reward["note"])

    def test_prepare_never_executes(self):
        with patch.object(settings, "web3_defi_enabled", True):
            result = DeFiIntelligenceService().prepare_action(
                "web3.defi.swap", {"protocol": "x", "chain_id": "11155111", "amount": 1}
            )
        self.assertTrue(result["approval_required"])
        self.assertFalse(result["execution_enabled"])


class X402Tests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_disabled_by_default(self):
        with self.assertRaises(ProviderDenied):
            await X402Service().discover("https://example.com/api")

    def test_evaluation_requires_verified_provider_and_budget(self):
        with patch.object(settings, "web3_x402_enabled", True):
            service = X402Service()
            denied = service.evaluate(price_usd=5, budget_usd=10, provider_reputation="unknown")
            allowed = service.evaluate(price_usd=5, budget_usd=10, provider_reputation="verified")
        self.assertFalse(denied["recommended"])
        self.assertTrue(allowed["recommended"])

    def test_preparation_has_no_payment(self):
        with patch.object(settings, "web3_x402_enabled", True):
            result = X402Service().prepare_purchase(
                service_url="https://example.com/api", amount_usd=1
            )
        self.assertFalse(result["execution_enabled"])
        self.assertTrue(result["escrow_required"])

    async def test_settlement_always_denied(self):
        with self.assertRaises(ProviderDenied):
            await X402Service().settle({})


class ContractTests(unittest.TestCase):
    def test_proxy_and_dangerous_construct_flags(self):
        with patch.object(settings, "web3_contract_dev_enabled", True):
            result = ContractIntelligenceService().analyze(
                abi=[{"name": "transfer"}, {"name": "balanceOf"}, {"name": "allowance"}],
                source="function x() public { selfdestruct(payable(msg.sender)); }",
                is_proxy=True,
                verified_source=False,
            )
        self.assertIn("ERC-20", result["detected_standards"])
        self.assertIn("dangerous_construct:selfdestruct", result["risk_flags"])
        self.assertIn("proxy_contract", result["risk_flags"])

    def test_production_deployment_denied(self):
        with patch.object(settings, "web3_contract_dev_enabled", True):
            with self.assertRaises(ProviderDenied):
                ContractIntelligenceService().prepare_deployment(
                    standard="ERC-20", chain_id="1", testnet=False
                )

    def test_template_is_marked_not_production_ready(self):
        source = ContractIntelligenceService.template("ERC-721")
        self.assertIn("NOT production ready", source)


class NftDaoBridgeTests(unittest.TestCase):
    def test_metadata_validation_and_mint_preparation(self):
        with patch.object(settings, "web3_nft_enabled", True):
            service = DigitalAssetService()
            self.assertFalse(service.validate_metadata_ref("not-a-ref")["valid"])
            result = service.prepare_mint(
                chain_id="11155111", standard="ERC-721", owner="0xabc",
                metadata_ref="ipfs://bafyexample",
            )
        self.assertTrue(result["approval_required"])
        self.assertFalse(result["execution_enabled"])

    def test_high_risk_dao_recommends_abstain(self):
        with patch.object(settings, "web3_dao_enabled", True):
            service = DaoGovernanceService()
            analysis = service.analyze_proposal(
                dao="test", proposal_id="1", summary="mint tokens",
                indicators=["unlimited_token_mint", "no_timelock"],
            )
            recommendation = service.recommendation(analysis)
        self.assertEqual(recommendation["recommendation"], "abstain")
        self.assertTrue(recommendation["advisory_only"])

    def test_bridge_quote_ranking_and_preparation(self):
        with patch.object(settings, "web3_cross_chain_enabled", True):
            service = CrossChainService()
            best = service.compare_routes([
                {"bridge": "unverified", "from_chain": "1", "to_chain": "8453",
                 "amount_out": 999, "verified": False},
                {"bridge": "checked", "from_chain": "1", "to_chain": "8453",
                 "amount_out": 90, "verified": True},
            ])["best"]
            prepared = service.prepare_bridge(
                bridge=best["bridge"], from_chain="1", to_chain="8453",
                token="USDC", amount=1, recipient="0xabc",
            )
        self.assertEqual(best["bridge"], "checked")
        self.assertTrue(prepared["approval_required"])


class RiskAndAnalysisTests(unittest.TestCase):
    def test_high_signal_can_not_be_overridden(self):
        with patch.object(settings, "web3_threat_intel_enabled", True):
            result = ThreatIntelService().assess(
                target="0xabc",
                signals=[
                    {"name": "drainer_contract", "source": "source-a"},
                    {"name": "low_risk_score", "source": "source-b"},
                ],
            )
        self.assertEqual(result["risk"], "high")
        self.assertEqual(result["decision"], "deny")

    def test_concentration_and_anomalies(self):
        with patch.object(settings, "web3_onchain_analysis_enabled", True):
            service = OnChainAnalysisService()
            concentration = service.holder_concentration(
                holders=[{"balance": 60}, {"balance": 30}, {"balance": 10}], total_supply=100
            )
            anomalies = service.anomaly_scores(values=[1, 1, 1, 1, 100])
        self.assertEqual(concentration["concentration"], "high")
        self.assertEqual(len(anomalies["anomalies"]), 1)

    def test_eip1559_fee_and_whales(self):
        fee = OnChainAnalysisService.eip1559_fee(10, 2)
        self.assertEqual(fee["max_fee_per_gas"], 22)
        with patch.object(settings, "web3_onchain_analysis_enabled", True):
            whales = OnChainAnalysisService().whale_activity(
                transfers=[{"from": "a", "to": "b", "amount": 200, "token": "X"}], threshold=100
            )
        self.assertEqual(whales["count"], 1)


if __name__ == "__main__":
    unittest.main()
