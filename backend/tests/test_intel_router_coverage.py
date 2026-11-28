"""Model selection fallbacks and free-only filtering are behaviour, not theatre."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.intel_router_service import IntelligenceRouter


class FakeResult:
    def __init__(self, rows=None, value=None):
        self.rows = rows or []
        self.value = value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.rows)

    def scalar_one_or_none(self):
        return self.value


class RouterSelectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_discovered_models_uses_configured_fallback(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=FakeResult([]))
        with patch.object(settings, "adaptive_model_enabled", False):
            result = await IntelligenceRouter(db).select_model("coding")
        self.assertEqual(result["provider"], "fallback")
        self.assertTrue(result["fallback_used"])

    async def test_paid_model_filtered_when_not_allowed(self):
        model = SimpleNamespace(
            capabilities=["coding"], is_free=False, quality_score=0.99,
            provider_id="p1", model_id="paid-model",
        )
        provider = SimpleNamespace(is_active=True, free_only=False, name="hosted")
        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[FakeResult([model]), FakeResult(value=provider)]
        )
        with patch.object(settings, "adaptive_model_enabled", False):
            result = await IntelligenceRouter(db).select_model("coding")
        self.assertEqual(result["provider"], "fallback")

    async def test_capability_requirement_is_enforced(self):
        model = SimpleNamespace(
            capabilities=["chat"], is_free=True, quality_score=0.9,
            provider_id="p1", model_id="chat-only",
        )
        db = AsyncMock()
        db.execute = AsyncMock(return_value=FakeResult([model]))
        with patch.object(settings, "adaptive_model_enabled", False):
            result = await IntelligenceRouter(db).select_model(
                "coding", required_capabilities=["coding"]
            )
        self.assertEqual(result["provider"], "fallback")


if __name__ == "__main__":
    unittest.main()
