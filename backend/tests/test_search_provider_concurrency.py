"""Independent free engines are queried in parallel and failures stay visible."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.search_provider_registry import SearchProviderRegistry


class SearchProviderConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_providers_run_concurrently(self):
        registry = SearchProviderRegistry()
        started = 0
        both_started = asyncio.Event()

        async def fake_call(name, *_args, **_kwargs):
            nonlocal started
            started += 1
            if started >= 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=2)
            return {"provider": name, "results": [{"url": "https://example.org/a"}]}, None

        with patch.object(registry, "call", new=AsyncMock(side_effect=fake_call)):
            outcomes = await registry.call_concurrent(
                ["wikipedia", "duckduckgo", "searxng"],
                "query",
                3,
                10.0,
                max_providers=2,
            )

        self.assertEqual(len(outcomes), 2)
        self.assertEqual([name for name, _, _ in outcomes], ["wikipedia", "duckduckgo"])

    async def test_unhealthy_provider_recovers_after_cooldown(self):
        registry = SearchProviderRegistry()
        with patch.object(settings, "iam_search_provider_order", "duckduckgo"):
            for _ in range(3):
                registry.record("duckduckgo", ok=False, error="rate limited")
            self.assertEqual(registry.chain(free_only=True), [])
            registry.state("duckduckgo").last_failure_at -= (
                settings.iam_search_provider_recovery_s + 1
            )
            self.assertEqual(registry.chain(free_only=True), ["duckduckgo"])

    async def test_failures_are_returned_not_swallowed(self):
        registry = SearchProviderRegistry()

        async def fake_call(name, *_args, **_kwargs):
            if name == "wikipedia":
                return {}, "provider wikipedia: not suitable"
            return {"provider": name, "results": [{"url": "https://example.org/b"}]}, None

        with patch.object(registry, "call", new=AsyncMock(side_effect=fake_call)):
            outcomes = await registry.call_concurrent(
                ["wikipedia", "duckduckgo"], "query", 3, 10.0, max_providers=2
            )

        errors = {name: error for name, _, error in outcomes}
        self.assertIn("not suitable", errors["wikipedia"])
        self.assertIsNone(errors["duckduckgo"])


if __name__ == "__main__":
    unittest.main()
