"""HTTP acceptance tests for the Doc 25 Amendment A research APIs.

No database server, network call or real credential is used: the DB dependency
is overridden with an in-memory session and auth is disabled for the test only.
"""

import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.deps import get_db_session
from app.core.auth_policy import required_scope
from app.core.config import settings
from app.main import app


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


class FinancialIntelligenceHttpTests(unittest.TestCase):
    def setUp(self):
        self.db = FakeDB()
        app.dependency_overrides[get_db_session] = lambda: self.db
        self.auth_patch = patch.object(settings, "auth_enabled", False)
        self.auth_patch.start()
        self.client = TestClient(app)  # no lifespan: no database or workers start

    def tearDown(self):
        self.auth_patch.stop()
        app.dependency_overrides.clear()

    def test_policies_are_read_only(self):
        prediction = self.client.get("/api/v1/prediction-markets/policy")
        adapter = self.client.get("/api/v1/prediction-markets/execution-adapter")
        gaming = self.client.get("/api/v1/gaming-intelligence/policy")
        investment = self.client.get("/api/v1/investment-intelligence/policy")

        self.assertEqual(prediction.status_code, 200)
        self.assertTrue(prediction.json()["research_only"])
        self.assertFalse(prediction.json()["execution_adapter_enabled"])
        self.assertEqual(adapter.status_code, 200)
        self.assertFalse(adapter.json()["enabled"])
        self.assertFalse(gaming.json()["wagering_enabled"])
        self.assertFalse(investment.json()["order_execution_enabled"])

    def test_research_flow_over_http(self):
        flags = [
            patch.object(settings, "prediction_markets_research_enabled", True),
            patch.object(settings, "prediction_markets_forecasting_enabled", True),
        ]
        for item in flags:
            item.start()
        try:
            market = self.client.post(
                "/api/v1/prediction-markets/markets",
                json={
                    "platform": "polymarket",
                    "market_ref": "http-1",
                    "event_name": "Will Z happen?",
                    "outcomes": ["yes", "no"],
                    "implied_probabilities": {"yes": 0.4, "no": 0.6},
                },
            )
            self.assertEqual(market.status_code, 200)
            market_id = market.json()["id"]

            estimate = self.client.post(
                f"/api/v1/prediction-markets/markets/{market_id}/estimates",
                json={"outcome": "yes", "iam_probability": 0.55, "evidence": ["news"]},
            )
            self.assertEqual(estimate.status_code, 200)

            comparison = self.client.get(
                f"/api/v1/prediction-markets/markets/{market_id}/comparison"
            )
            self.assertEqual(comparison.status_code, 200)
            self.assertEqual(
                comparison.json()["comparisons"][0]["difference_percentage_points"], 15.0
            )

            forecast = self.client.post(
                "/api/v1/prediction-markets/forecast/run",
                json={
                    "market_id": market_id,
                    "method": "evidence_weighted",
                    "evidence": [
                        {"outcome": "yes", "strength": 0.6, "source": "news", "description": "x"},
                        {"outcome": "no", "strength": 0.3, "source": "history", "description": "y"},
                    ],
                    "rationale": "documented research",
                },
            )
            self.assertEqual(forecast.status_code, 200)
            self.assertTrue(forecast.json()["independent"])
            self.assertFalse(forecast.json()["market_implied_probabilities_used"])

            runs = self.client.get(f"/api/v1/prediction-markets/forecast/runs/{market_id}")
            self.assertEqual(runs.status_code, 200)
            self.assertEqual(len(runs.json()), 1)

            gaming = self.client.post(
                "/api/v1/gaming-intelligence/rtp-scenario",
                json={"rtp": 0.96, "wager": 100, "plays": 1},
            )
            self.assertEqual(gaming.status_code, 200)
            self.assertEqual(gaming.json()["expected_loss"], 4.0)
        finally:
            for item in reversed(flags):
                item.stop()

    def test_no_execution_route_exists(self):
        for path in (
            "/api/v1/prediction-markets/execute",
            "/api/v1/gaming-intelligence/wager",
            "/api/v1/investment-intelligence/orders",
        ):
            self.assertEqual(self.client.post(path, json={}).status_code, 404)

    def test_new_paths_require_admin_scope(self):
        for path in (
            "/api/v1/prediction-markets/policy",
            "/api/v1/gaming-intelligence/policy",
            "/api/v1/investment-intelligence/policy",
            "/api/v1/provider-registry/entries",
        ):
            self.assertEqual(required_scope(path), "admin")

    def test_research_flag_blocks_market_registration(self):
        with patch.object(settings, "prediction_markets_research_enabled", False):
            response = self.client.post(
                "/api/v1/prediction-markets/markets",
                json={
                    "platform": "polymarket",
                    "market_ref": "blocked",
                    "event_name": "blocked",
                    "outcomes": ["yes"],
                    "implied_probabilities": {"yes": 0.5},
                },
            )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
