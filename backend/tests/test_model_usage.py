"""OD-51 §4.3: fail-closed usage accounting and persisted attribution."""

import unittest
from decimal import Decimal
from unittest.mock import patch

from app.models.globalaccess import RequestUsage
from app.models.model_provider_key import ModelProviderKey
from app.models.modelrouter import DiscoveredModel, ProviderUsage
from app.services.crypto_service import crypto
from app.services.model_usage import ModelUsageService


class FakeResult:
    def __init__(self, rows):
        self.rows = list(rows)

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    async def execute(self, statement):
        try:
            froms = list(statement.froms)
            name = getattr(froms[0], "name", "") if froms else ""
        except Exception:
            name = str(statement)
        return FakeResult(
            [r for r in self.rows if getattr(r.__class__, "__tablename__", "") in name]
        )

    def add(self, obj):
        self.rows.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None


def _model(price_in=Decimal("1.000000"), price_out=Decimal("2.000000")):
    return DiscoveredModel(
        model_id="nvidia-test-model",
        is_free=False,
        cost_input_per_1m=price_in,
        cost_output_per_1m=price_out,
    )


AUTH = {"authorized": True, "authorization_id": "signed-1"}


class ModelUsageTests(unittest.IsolatedAsyncioTestCase):
    async def test_free_request_is_allowed_without_authorization(self):
        decision = await ModelUsageService(FakeDB()).preflight(
            model="local-qwen-coder-3b", is_paid=False
        )
        self.assertTrue(decision.allowed)

    async def test_paid_request_without_authorization_is_denied(self):
        db = FakeDB([_model()])
        decision = await ModelUsageService(db).preflight(model="nvidia-test-model", is_paid=True)
        self.assertFalse(decision.allowed)
        self.assertIn("authorisation", decision.reason)

    async def test_paid_request_without_price_is_denied(self):
        db = FakeDB([])
        with patch("app.services.model_usage.settings.finance_monthly_limit_usd", 100.0):
            decision = await ModelUsageService(db).preflight(
                model="nvidia-test-model", is_paid=True, authorization=AUTH
            )
        self.assertFalse(decision.allowed)
        self.assertIn("cost", decision.reason)

    async def test_paid_request_without_budget_is_denied(self):
        db = FakeDB([_model()])
        with patch("app.services.model_usage.settings.finance_monthly_limit_usd", 0):
            decision = await ModelUsageService(db).preflight(
                model="nvidia-test-model", is_paid=True, authorization=AUTH
            )
        self.assertFalse(decision.allowed)
        self.assertIn("limit", decision.reason)

    async def test_budget_exhaustion_denies_request(self):
        spent = ProviderUsage(
            model_id="nvidia-test-model",
            tokens_input=1000,
            tokens_output=1000,
            estimated_cost_usd=Decimal("100.000000"),
            period=__import__("datetime").datetime.now().strftime("%Y-%m"),
        )
        db = FakeDB([_model(), spent])
        with patch("app.services.model_usage.settings.finance_monthly_limit_usd", 10.0):
            decision = await ModelUsageService(db).preflight(
                model="nvidia-test-model", is_paid=True, authorization=AUTH
            )
        self.assertFalse(decision.allowed)

    async def test_authorised_budgeted_request_is_allowed_and_estimated(self):
        db = FakeDB([_model()])
        with patch("app.services.model_usage.settings.finance_monthly_limit_usd", 100.0):
            decision = await ModelUsageService(db).preflight(
                model="nvidia-test-model", is_paid=True, authorization=AUTH
            )
        self.assertTrue(decision.allowed)
        self.assertAlmostEqual(decision.estimated_cost_usd, 0.003)

    async def test_record_persists_usage_with_attribution(self):
        db = FakeDB([_model()])
        decision = await ModelUsageService(db).preflight(
            model="nvidia-test-model", is_paid=False
        )
        result = await ModelUsageService(db).record(
            model="nvidia-test-model",
            provider="nvidia",
            usage={"prompt_tokens": 1000, "completion_tokens": 500},
            is_paid=False,
            decision=decision,
            key_fingerprint="abc123",
        )
        self.assertTrue(any(isinstance(r, ProviderUsage) for r in db.rows))
        self.assertTrue(any(isinstance(r, RequestUsage) for r in db.rows))
        self.assertEqual(result["key_fingerprint"], "abc123")
        self.assertEqual(result["tokens_input"], 1000)
        self.assertAlmostEqual(result["cost_usd"], 0.002)


if __name__ == "__main__":
    unittest.main()
