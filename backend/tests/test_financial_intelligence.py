"""Doc 25 Amendment A — research-only prediction, gaming and investment modules."""

import unittest
import uuid
from unittest.mock import patch

import httpx

from app.core.config import settings
from app.models.security import AuditEvent
from app.services.financial_intelligence.policy import IntelligenceDenied
from app.services.financial_intelligence.provider_registry import ProviderRegistryService
from app.services.gaming_intelligence.service import GamingDenied, GamingIntelligenceService
from app.services.investment_intelligence.service import InvestmentDenied, InvestmentIntelligenceService
from app.services.prediction_markets.adapter import DataAdapterDenied, PolymarketDataAdapter
from app.services.prediction_markets.forecasting import ForecastDenied, ForecastEngine
from app.services.prediction_markets.service import PredictionMarketDenied, PredictionMarketService


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


class PredictionMarketTests(unittest.IsolatedAsyncioTestCase):
    async def test_research_only_policy_and_disabled_execution(self):
        service = PredictionMarketService(FakeDB())
        policy = service.policy()
        self.assertTrue(policy["research_only"])
        self.assertFalse(policy["execution_adapter_enabled"])
        self.assertFalse(service.execution_adapter()["enabled"])
        self.assertIn("polymarket", policy["platforms"])
        with self.assertRaises(PredictionMarketDenied):
            await service.execute()

    async def test_probability_comparison_and_legal_gate(self):
        db = FakeDB()
        service = PredictionMarketService(db)
        with patch.object(settings, "prediction_markets_research_enabled", True):
            market = await service.register_market(
                platform="polymarket",
                market_ref="btc-100k-2026",
                event_name="Will BTC reach 100k by 2026?",
                outcomes=["yes", "no"],
                implied_probabilities={"yes": 0.40, "no": 0.60},
                actor="iam",
            )
            self.assertTrue(market["research_only"])
            self.assertFalse(market["real_money_enabled"])
            await service.record_estimate(
                market_id=market["id"],
                outcome="yes",
                iam_probability=0.55,
                evidence=["historical volume", "macro data"],
                actor="iam",
            )
            comparison = await service.compare(market["id"])
            row = comparison["comparisons"][0]
            self.assertEqual(row["difference_percentage_points"], 15.0)
            self.assertTrue(comparison["not_profitable_by_itself"])
            self.assertFalse(comparison["execution_adapter_enabled"])

            with patch(
                "app.services.prediction_markets.service.CreatorApprovalService",
                approvals(False),
            ):
                with self.assertRaises(PredictionMarketDenied):
                    await service.request_legal_clearance(market["id"], "fake", "iam")
            with patch(
                "app.services.prediction_markets.service.CreatorApprovalService",
                approvals(True),
            ):
                cleared = await service.request_legal_clearance(market["id"], "signed", "iam")
            self.assertEqual(cleared["legal_status"], "cleared")
            self.assertFalse(cleared["real_money_enabled"])
            self.assertTrue(cleared["execution_still_disabled"])

        events = [row.event_type for row in db.rows if isinstance(row, AuditEvent)]
        self.assertIn("prediction_market_discovered", events)
        self.assertIn("prediction_probability_recorded", events)
        self.assertIn("prediction_market_legal_clearance_recorded", events)

    async def test_research_disabled_by_default(self):
        with patch.object(settings, "prediction_markets_research_enabled", False):
            with self.assertRaises(PredictionMarketDenied):
                await PredictionMarketService(FakeDB()).register_market(
                    platform="polymarket",
                    market_ref="m1",
                    event_name="event",
                    outcomes=["yes"],
                    implied_probabilities={"yes": 0.5},
                )


class GamingIntelligenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_wagering_and_funding_always_denied(self):
        service = GamingIntelligenceService(FakeDB())
        self.assertTrue(service.policy()["research_only"])
        self.assertFalse(service.policy()["wagering_enabled"])
        with self.assertRaises(GamingDenied):
            await service.wager()
        with self.assertRaises(GamingDenied):
            await service.fund_account()

    async def test_rtp_mathematics_is_long_run_only(self):
        service = GamingIntelligenceService(FakeDB())
        scenario = service.rtp_scenario(0.96, 100, 1)
        self.assertEqual(scenario["theoretical_return"], 96.0)
        self.assertEqual(scenario["expected_loss"], 4.0)
        self.assertIn("not a guaranteed outcome", scenario["disclaimer"])

    async def test_analysis_recorded_as_research(self):
        db = FakeDB()
        service = GamingIntelligenceService(db)
        with patch.object(settings, "gaming_intelligence_enabled", True):
            record = await service.record_analysis(
                game="european-roulette",
                rtp=0.9729,
                house_edge=0.0271,
                methodology="simulation over independent spins",
                sample_size=100000,
                findings={"rng": "independent"},
            )
        self.assertFalse(record["wagering_enabled"])
        self.assertTrue(
            any(
                row.event_type == "gaming_analysis_recorded"
                for row in db.rows
                if isinstance(row, AuditEvent)
            )
        )
        with self.assertRaises(GamingDenied):
            await service.record_analysis(game="slots", rtp=1.5, house_edge=0.1, methodology="x")


class InvestmentIntelligenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_thesis_and_rebalance_are_research_only(self):
        db = FakeDB()
        service = InvestmentIntelligenceService(db)
        with patch.object(settings, "investment_intelligence_research_enabled", True):
            thesis = await service.record_thesis(
                asset_class="etfs",
                symbol="ETF-X",
                thesis="diversified exposure",
                risk_notes="market risk",
            )
            self.assertFalse(thesis["execution_enabled"])
            proposal = await service.record_rebalance_proposal(
                portfolio_ref="demo",
                allocations={"ETF-X": 0.6, "BONDS": 0.4},
                rationale="risk balance",
            )
            self.assertEqual(proposal["asset_class"], "portfolio")
            self.assertFalse(proposal["execution_enabled"])
            with self.assertRaises(InvestmentDenied):
                await service.record_rebalance_proposal(
                    portfolio_ref="demo", allocations={"A": 0.5}, rationale="bad sum"
                )
            with self.assertRaises(InvestmentDenied):
                await service.place_order()
        self.assertTrue(
            any(
                row.event_type == "investment_thesis_recorded"
                for row in db.rows
                if isinstance(row, AuditEvent)
            )
        )


class ProviderRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_adapter_requires_every_gate(self):
        db = FakeDB()
        service = ProviderRegistryService(db)
        with patch.object(settings, "financial_provider_registry_enabled", True):
            await service.register(
                name="Example Data",
                category="market_data",
                access_model="free",
                documented_api_and_auth=True,
                actor="iam",
            )
            evaluation = await service.evaluate("Example Data")
            self.assertFalse(evaluation["adapter_eligible"])
            self.assertIn("commercial_use_permitted", evaluation["missing"])
            with self.assertRaises(IntelligenceDenied):
                await service.enable_adapter("Example Data", "iam")

            await service.register(
                name="Cleared Data",
                category="market_data",
                access_model="paid",
                documented_api_and_auth=True,
                commercial_use=True,
                automated_use=True,
                south_africa_supported=True,
                sandbox_available=True,
                licence_requirements_recorded=True,
                gates_reviewed=True,
                actor="iam",
            )
            enabled = await service.enable_adapter("Cleared Data", "iam")
            self.assertTrue(enabled["adapter_enabled"])
        self.assertTrue(
            any(
                row.event_type == "financial_provider_adapter_enabled"
                for row in db.rows
                if isinstance(row, AuditEvent)
            )
        )


class ProviderCatalogueTests(unittest.IsolatedAsyncioTestCase):
    async def test_seed_is_idempotent_and_enables_nothing(self):
        db = FakeDB()
        service = ProviderRegistryService(db)
        first = await service.seed_candidates("iam")
        self.assertEqual(first["created"], first["candidates"])
        self.assertTrue(first["all_adapters_disabled"])

        second = await service.seed_candidates("iam")
        self.assertEqual(second["created"], 0)
        self.assertEqual(second["existing"], first["candidates"])

        entries = await service.entries()
        self.assertEqual(len(entries), first["candidates"])
        self.assertTrue(all(not row["adapter_enabled"] for row in entries))
        self.assertTrue(all(not row["gates_reviewed"] for row in entries))
        self.assertTrue(
            all(not row["south_africa_supported"] for row in entries)
        )

        with self.assertRaises(IntelligenceDenied):
            await service.enable_adapter("Polymarket", "iam")
        with patch.object(settings, "financial_provider_registry_enabled", True):
            evaluation = await service.evaluate("Polymarket")
        self.assertFalse(evaluation["adapter_eligible"])
        self.assertIn("gates_reviewed", evaluation["missing"])

        polymarket = next(row for row in entries if row["name"] == "Polymarket")
        self.assertIn("South African legal status", polymarket["notes"])
        gaming = next(row for row in entries if row["name"] == "Evolution")
        self.assertIn("no wagering", gaming["notes"])

        self.assertEqual(
            sum(
                1
                for row in db.rows
                if isinstance(row, AuditEvent)
                and row.event_type == "financial_provider_catalogue_seeded"
            ),
            1,
        )


class PolymarketDataAdapterTests(unittest.IsolatedAsyncioTestCase):
    def _settings(self, **overrides):
        values = {
            "prediction_markets_research_enabled": True,
            "prediction_markets_data_adapter_enabled": True,
            "prediction_markets_gamma_url": "https://gamma.example.invalid",
            "prediction_markets_clob_url": "https://clob.example.invalid",
            "prediction_markets_data_url": "https://data.example.invalid",
        }
        values.update(overrides)
        return [patch.object(settings, key, value) for key, value in values.items()]

    def test_policy_is_read_only(self):
        adapter = PolymarketDataAdapter(FakeDB())
        policy = adapter.policy()
        self.assertTrue(policy["get_only"])
        self.assertFalse(policy["trading_enabled"])
        self.assertFalse(policy["wallet_access_enabled"])
        self.assertTrue(policy["records_market_implied_probability_only"])

    async def test_disabled_adapter_performs_no_request(self):
        requested = []

        def handler(request):
            requested.append(request)
            return httpx.Response(200, json=[])

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with patch.object(settings, "prediction_markets_data_adapter_enabled", False):
                with self.assertRaises(DataAdapterDenied):
                    await PolymarketDataAdapter(FakeDB(), client).sync_markets()
        self.assertEqual(requested, [])

    async def test_sync_records_implied_probability_only_and_is_idempotent(self):
        payload = [
            {
                "id": "m1",
                "question": "Will X happen?",
                "outcomes": '["Yes","No"]',
                "outcomePrices": '["0.4","0.6"]',
                "closed": False,
                "url": "https://polymarket.com/event/x",
            },
            {
                "id": "m2",
                "question": "Malformed outcomes?",
                "outcomes": '["Yes"]',
                "outcomePrices": '["0.4","0.6"]',
                "closed": False,
            },
        ]
        methods = []

        def handler(request):
            methods.append(request.method)
            return httpx.Response(200, json=payload)

        db = FakeDB()
        patches = self._settings()
        for item in patches:
            item.start()
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                adapter = PolymarketDataAdapter(db, client)
                first = await adapter.sync_markets("iam")
                markets = await PredictionMarketService(db).markets()
                estimates = await PredictionMarketService(db).estimates(markets[0]["id"])
                second = await adapter.sync_markets("iam")
        finally:
            for item in reversed(patches):
                item.stop()

        self.assertEqual(first["discovered"], 1)  # malformed outcome row filtered at fetch
        self.assertEqual(first["created"], 1)
        self.assertEqual(first["skipped"], 0)
        self.assertEqual(second["existing"], 1)
        self.assertEqual(second["created"], 0)
        self.assertEqual(markets[0]["implied_probabilities"], {"Yes": 0.4, "No": 0.6})
        self.assertEqual(estimates, [])
        self.assertEqual(set(methods), {"GET"})
        self.assertTrue(
            any(
                row.event_type == "prediction_market_data_synced"
                for row in db.rows
                if isinstance(row, AuditEvent)
            )
        )

    async def test_order_book_is_read_only_and_bounded(self):
        methods = []

        def handler(request):
            methods.append((request.method, request.url.path))
            return httpx.Response(
                200,
                json={
                    "bids": [{"price": str(0.4 - i), "size": "10"} for i in range(10)],
                    "asks": [{"price": str(0.4 + i), "size": "10"} for i in range(10)],
                },
            )

        patches = self._settings(prediction_markets_book_depth=3)
        for item in patches:
            item.start()
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                book = await PolymarketDataAdapter(FakeDB(), client).fetch_order_book("tok")
        finally:
            for item in reversed(patches):
                item.stop()

        self.assertEqual(len(book["levels"]), 6)
        self.assertTrue(book["read_only"])
        self.assertEqual(book["orders_placed"], 0)
        self.assertEqual(methods, [("GET", "/book")])

    async def test_data_path_validation_and_https_guard(self):
        def handler(request):
            return httpx.Response(200, json={"ok": True})

        patches = self._settings()
        for item in patches:
            item.start()
        try:
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                adapter = PolymarketDataAdapter(FakeDB(), client)
                self.assertEqual(await adapter.fetch_data("/activity"), {"ok": True})
                with self.assertRaises(DataAdapterDenied):
                    await adapter.fetch_data("../markets")
                with self.assertRaises(DataAdapterDenied):
                    await adapter.fetch_data("https://evil.invalid/markets")

            with patch.object(settings, "prediction_markets_gamma_url", "http://gamma.invalid"):
                with self.assertRaises(DataAdapterDenied):
                    await adapter.fetch_markets()
        finally:
            for item in reversed(patches):
                item.stop()


class ForecastEngineTests(unittest.IsolatedAsyncioTestCase):
    async def _market(self, db):
        with patch.object(settings, "prediction_markets_research_enabled", True):
            return await PredictionMarketService(db).register_market(
                platform="polymarket",
                market_ref="forecast-1",
                event_name="Will Y happen?",
                outcomes=["yes", "no"],
                implied_probabilities={"yes": 0.40, "no": 0.60},
            )

    def test_compute_is_normalised_and_independent(self):
        result = ForecastEngine.compute(
            "evidence_weighted",
            ["yes", "no"],
            [
                {"outcome": "yes", "strength": 0.6, "source": "news", "description": "support"},
                {"outcome": "no", "strength": 0.3, "source": "history", "description": "counter"},
            ],
        )
        self.assertAlmostEqual(sum(result["probabilities"].values()), 1.0)
        self.assertGreater(result["probabilities"]["yes"], result["probabilities"]["no"])
        self.assertEqual(result["confidence"], 0.9)
        self.assertFalse(result["market_implied_probabilities_used"])
        self.assertIn("score(outcome)", result["formula"])

    async def test_run_records_evidence_estimates_and_comparison(self):
        db = FakeDB()
        market = await self._market(db)
        evidence = [
            {"outcome": "yes", "strength": 0.6, "source": "news", "description": "support"},
            {"outcome": "no", "strength": 0.3, "source": "history", "description": "counter"},
        ]
        with patch.object(settings, "prediction_markets_forecasting_enabled", True):
            with patch.object(settings, "prediction_markets_research_enabled", True):
                result = await ForecastEngine(db).run(
                    market_id=market["id"],
                    method="evidence_weighted",
                    evidence=evidence,
                    rationale="news outweighs history",
                )
                runs = await ForecastEngine(db).runs(market["id"])

        self.assertTrue(result["independent"])
        self.assertFalse(result["market_implied_probabilities_used"])
        self.assertEqual(len(result["estimates"]), 2)
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["method"], "evidence_weighted")
        self.assertEqual(runs[0]["rationale"], "news outweighs history")
        self.assertEqual(len(runs[0]["evidence"]), 2)
        self.assertFalse(runs[0]["market_implied_probabilities_used"])
        self.assertEqual(result["comparison"]["comparisons"][0]["market_probability"], 0.4)
        self.assertTrue(
            any(
                row.event_type == "prediction_forecast_recorded"
                for row in db.rows
                if isinstance(row, AuditEvent)
            )
        )

    async def test_invalid_evidence_and_disabled_engine_are_denied(self):
        db = FakeDB()
        market = await self._market(db)
        with self.assertRaises(ForecastDenied):
            await ForecastEngine.compute("unknown", ["yes"], [])
        with self.assertRaises(ForecastDenied):
            ForecastEngine.compute("evidence_weighted", ["yes"], [])
        with self.assertRaises(ForecastDenied):
            ForecastEngine.compute(
                "evidence_weighted",
                ["yes", "no"],
                [{"outcome": "maybe", "strength": 0.5, "source": "x"}],
            )
        with self.assertRaises(ForecastDenied):
            ForecastEngine.compute(
                "evidence_weighted",
                ["yes", "no"],
                [{"outcome": "yes", "strength": 1.5, "source": "x"}],
            )
        with patch.object(settings, "prediction_markets_forecasting_enabled", False):
            with self.assertRaises(ForecastDenied):
                await ForecastEngine(db).run(
                    market_id=market["id"],
                    method="evidence_weighted",
                    evidence=[{"outcome": "yes", "strength": 0.6, "source": "x"}],
                    rationale="test",
                )


if __name__ == "__main__":
    unittest.main()
