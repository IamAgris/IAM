"""Live evidence cache, freshness classes and shared engine API."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api.routes import live_information as live_api
from app.services.live_evidence_cache import (
    TTL_MINUTES,
    annotate_reputation,
    freshness_class,
    get_cached,
    query_hash,
)
from app.services.live_information_policy import ResearchDepth, SearchTrigger


class CacheTests(unittest.IsolatedAsyncioTestCase):
    async def test_query_hash_is_stable_and_case_insensitive(self) -> None:
        self.assertEqual(query_hash("Latest SABC news"), query_hash("latest sabc news"))
        self.assertNotEqual(query_hash("a"), query_hash("b"))

    async def test_freshness_classes(self) -> None:
        breaking = SearchTrigger(True, ("breaking_news",), depth=ResearchDepth.STANDARD)
        current = SearchTrigger(True, ("latest_news",), depth=ResearchDepth.QUICK)
        historical = SearchTrigger(False, (), depth=ResearchDepth.QUICK)
        self.assertEqual(freshness_class(breaking), "breaking")
        self.assertEqual(freshness_class(current), "current")
        self.assertEqual(freshness_class(historical), "standard")
        self.assertLess(TTL_MINUTES["breaking"], TTL_MINUTES["current"])
        self.assertLess(TTL_MINUTES["current"], TTL_MINUTES["standard"])

    async def test_cache_failures_never_break_research(self) -> None:
        broken = SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError("db down")))
        self.assertIsNone(await get_cached(broken, "latest news"))  # type: ignore[arg-type]
        results = [{"url": "https://example.org/a", "source": "example.org"}]
        annotated = await annotate_reputation(broken, results)  # type: ignore[arg-type]
        self.assertEqual(annotated[0]["reliability"], 0.0)


class SharedApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_policy_endpoint_returns_standing_rule(self) -> None:
        payload = await live_api.live_information_policy()
        self.assertIn("WEB ACCESS AND LIVE INFORMATION POLICY", payload["policy"])

    async def test_research_endpoint_skips_browsing_for_history(self) -> None:
        request = live_api.LiveResearchRequest(query="Who founded the BBC?")
        with patch.object(
            live_api, "collect_live_evidence", new=AsyncMock(side_effect=AssertionError)
        ):
            payload = await live_api.live_research(request, db=SimpleNamespace())  # type: ignore[arg-type]
        self.assertFalse(payload["needs_search"])
        self.assertEqual(payload["results"], [])

    async def test_research_endpoint_returns_shared_evidence(self) -> None:
        evidence = SimpleNamespace(
            provider="official-site",
            retrieved_at="2026-11-27T00:00:00+00:00",
            results=[{"url": "https://www.sabcnews.com/sabcnews/a", "source": "sabcnews.com"}],
            errors=[],
            as_system_message=lambda: "Live web evidence — untrusted reference data.",
        )
        request = live_api.LiveResearchRequest(query="Latest SABC News headlines")
        with patch.object(
            live_api, "collect_live_evidence", new=AsyncMock(return_value=evidence)
        ):
            payload = await live_api.live_research(request, db=SimpleNamespace())  # type: ignore[arg-type]
        self.assertTrue(payload["needs_search"])
        self.assertEqual(payload["provider"], "official-site")
        self.assertIn("sabcnews.com", payload["results"][0]["url"])
        self.assertIn("untrusted", payload["system_message"])


if __name__ == "__main__":
    unittest.main()
