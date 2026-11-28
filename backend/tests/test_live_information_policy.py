"""Live-information policy: standing instruction, triggers and wired auto-search."""

import unittest
from typing import Any, Dict, Optional
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api.routes import models
from app.core.config import settings
from app.services import browser_service as browser_service_module
from app.services import search_service as search_service_module
from app.services.live_information_policy import (
    LiveEvidence,
    ResearchDepth,
    SearchTriggerClassifier,
    WEB_ACCESS_POLICY,
    with_live_policy,
)


class PolicyTests(unittest.TestCase):
    def test_policy_contains_forbidden_disclaimer_and_is_injected_first(self) -> None:
        self.assertIn("WEB ACCESS AND LIVE INFORMATION POLICY", WEB_ACCESS_POLICY)
        self.assertIn("As an AI language model, I don't have access", WEB_ACCESS_POLICY)
        messages = [{"role": "system", "content": "You are IAM."}, {"role": "user", "content": "hi"}]
        result = with_live_policy(messages)
        self.assertEqual(result[0]["content"], WEB_ACCESS_POLICY)
        self.assertEqual([m["role"] for m in result], ["system", "system", "user"])

    def test_policy_injection_is_idempotent(self) -> None:
        once = with_live_policy([{"role": "user", "content": "hi"}])
        twice = with_live_policy(once)
        self.assertEqual(len(once), len(twice))
        self.assertEqual(once, twice)

    def test_classifier_categories(self) -> None:
        classifier = SearchTriggerClassifier()
        cases = {
            "What's the latest news from SABC?": ("latest_news", True),
            "Breaking news right now": ("breaking_news", True),
            "Search the web for the current price of petrol": ("explicit_search", True),
            "What is the weather forecast today?": ("weather", True),
            "Who won the final score in the match?": ("sports_results", True),
        }
        for query, (category, expected) in cases.items():
            with self.subTest(query=query):
                trigger = classifier.classify(query)
                self.assertEqual(trigger.needs_search, expected)
                self.assertIn(category, trigger.categories)

    def test_source_first_without_triggering_on_history(self) -> None:
        classifier = SearchTriggerClassifier()
        current = classifier.classify("Latest SABC News headlines")
        self.assertTrue(current.needs_search)
        self.assertIn("sabcnews.com", current.preferred_sources)
        self.assertEqual(current.depth, ResearchDepth.STANDARD)

        historical = classifier.classify("Who founded the BBC?")
        self.assertFalse(historical.needs_search)
        self.assertIn("bbc.com", historical.preferred_sources)

    def test_user_url_becomes_preferred_source(self) -> None:
        trigger = SearchTriggerClassifier().classify(
            "Read https://example.org/report.html for me"
        )
        self.assertTrue(trigger.needs_search)
        self.assertIn("example.org", trigger.preferred_sources)

    def test_deep_research_depth(self) -> None:
        trigger = SearchTriggerClassifier().classify(
            "Compare and comprehensively investigate the new AI model releases"
        )
        self.assertEqual(trigger.depth, ResearchDepth.DEEP)

    def test_evidence_message_cites_source_date_and_url(self) -> None:
        evidence = LiveEvidence(
            query="latest news",
            retrieved_at="2026-11-27T10:00:00+00:00",
            provider="wikipedia",
            results=[
                {
                    "title": "Story",
                    "url": "https://www.sabcnews.com/story",
                    "description": "Extracted article text.",
                    "published": "2026-11-27",
                    "source": "www.sabcnews.com",
                }
            ],
        )
        message = evidence.as_system_message()
        self.assertIn("untrusted reference data", message)
        self.assertIn("2026-11-27", message)
        self.assertIn("https://www.sabcnews.com/story", message)
        self.assertIn("Extracted article text.", message)

    def test_failure_is_reported_not_fabricated(self) -> None:
        evidence = LiveEvidence(
            query="latest news",
            retrieved_at="2026-11-27T10:00:00+00:00",
            provider="unavailable",
            errors=["search failed: TimeoutError"],
        )
        message = evidence.as_system_message()
        self.assertIn("No live evidence was retrieved", message)
        self.assertIn("search failed", message)


class AutoSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_collect_evidence_uses_existing_search_service(self) -> None:
        from app.services import live_information_policy as policy

        payload = {
            "query": "latest news",
            "provider": "brave",
            "results": [
                {"title": "A", "url": "https://sabcnews.com/a", "description": "snippet", "age": "2h"}
            ],
        }
        with patch.object(
            search_service_module.search_service,
            "search",
            new=AsyncMock(return_value=payload),
        ) as mocked:
            evidence = await policy.collect_live_evidence("latest news")
        # Independent free engines are queried concurrently now; all outcomes
        # are merged, so more than one adapter call is expected.
        self.assertGreaterEqual(mocked.await_count, 1)
        self.assertLessEqual(mocked.await_count, settings.iam_search_concurrent_providers)
        self.assertEqual(len(evidence.results), 1)
        self.assertEqual(evidence.results[0]["source"], "sabcnews.com")
        self.assertEqual(evidence.results[0]["published"], "2h")

    async def test_prepare_messages_injects_policy_and_live_evidence(self) -> None:
        request = models.ChatRequest(
            messages=[
                models.ChatMessage(
                    role="user", content="What's the latest news from SABC?"
                )
            ]
        )
        status = SimpleNamespace(mode="ollama", model=settings.iam_primary_model)
        evidence = LiveEvidence(
            query="latest news",
            retrieved_at="2026-11-27T10:00:00+00:00",
            provider="wikipedia",
            results=[
                {
                    "title": "Story",
                    "url": "https://www.sabcnews.com/story",
                    "description": "Artifact text.",
                    "published": "2026-11-27",
                    "source": "www.sabcnews.com",
                }
            ],
        )
        with (
            patch.object(
                models,
                "assemble_context",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        as_system_message=lambda: None,
                        knowledge_message=lambda: None,
                    )
                ),
            ),
            patch.object(
                models, "collect_live_evidence", new=AsyncMock(return_value=evidence)
            ) as mocked,
        ):
            result, delegation, action, conversation_id = await models._prepare_messages(
                request, SimpleNamespace(), status
            )
        mocked.assert_awaited_once()
        self.assertIsNone(delegation)
        self.assertIsNone(action)
        self.assertEqual(result[0]["content"], WEB_ACCESS_POLICY)
        joined = "\n".join(m["content"] for m in result if m["role"] == "system")
        self.assertIn("https://www.sabcnews.com/story", joined)
        self.assertIn("collected by IAM's Web Intelligence Engine", joined)



class LiveRetrievalAcceptanceTests(unittest.IsolatedAsyncioTestCase):
    """Acceptance cases required before OD-54 can be recorded."""

    async def collect(
        self,
        query: str,
        configured: Dict[str, Any],
        browser: AsyncMock,
        official: Optional[Dict[str, Any]] = None,
        free: Optional[Dict[str, Any]] = None,
    ) -> LiveEvidence:
        from app.services import live_information_policy as policy

        async def provider_search(
            query: str, max_results: int = 10, provider: Optional[str] = None
        ) -> Dict[str, Any]:
            if provider == "duckduckgo":
                return free or {"provider": "duckduckgo", "query": query, "results": []}
            if provider == "searxng":
                return {"provider": "searxng", "query": query, "results": []}
            return configured

        from app.services.search_provider_registry import search_provider_registry

        search_provider_registry.reset()
        with (
            patch.object(settings, "iam_search_provider_order", "wikipedia,duckduckgo"),
            patch.object(
                search_service_module.search_service,
                "search",
                new=AsyncMock(side_effect=provider_search),
            ),
            patch.object(
                browser_service_module.browser_service,
                "search_duckduckgo",
                new=browser,
            ),
            patch.object(
                browser_service_module.browser_service,
                "fetch_page",
                new=AsyncMock(
                    return_value=official or {"links": [], "text": ""}
                ),
            ),
        ):
            return await policy.collect_live_evidence(query)

    async def test_01_sabc_news_without_api_key_escalates_to_browser(self) -> None:
        calls = []

        async def browser(query: str, max_results: int = 10) -> list[dict[str, str]]:
            calls.append(query)
            if "site:sabcnews.com" in query:
                return [
                    {
                        "title": "SABC breaking story",
                        "url": "https://www.sabcnews.com/sabcnews/latest-story",
                        "snippet": "Actual SABC reporting.",
                    }
                ]
            return []

        official = {
            "text": "TOP STORIES\nMadlanga Commission hears evidence\n 27 November 2026, 5:43 AM",
            "links": [
                {
                    "text": "Madlanga Commission hears evidence",
                    "url": "https://www.sabcnews.com/sabcnews/madlanga-hears-evidence/",
                }
            ],
        }
        evidence = await self.collect(
            "What's the latest news from SABC?",
            {"provider": "wikipedia", "results": []},
            AsyncMock(side_effect=browser),
            official=official,
        )
        self.assertIn("official-site", evidence.provider)
        self.assertTrue(evidence.results)
        self.assertIn("27 November 2026", evidence.results[0]["published"])
        self.assertIn("not suitable as current information", " ".join(evidence.errors))

    async def test_02_actual_sabc_article_content_and_url_in_evidence(self) -> None:
        async def browser(query: str, max_results: int = 10) -> list[dict[str, str]]:
            if "site:sabcnews.com" in query:
                return [
                    {
                        "title": "SABC article",
                        "url": "https://www.sabcnews.com/sabcnews/article-42",
                        "snippet": "Verified article body text.",
                    }
                ]
            return []

        official = {
            "text": "TOP STORIES\nVerified article body text.\n 27 November 2026",
            "links": [
                {
                    "text": "SABC article",
                    "url": "https://www.sabcnews.com/sabcnews/article-42",
                }
            ],
        }
        evidence = await self.collect(
            "Latest SABC News headlines",
            {"provider": "wikipedia", "results": []},
            AsyncMock(side_effect=browser),
            official=official,
        )
        message = evidence.as_system_message()
        self.assertIn("https://www.sabcnews.com/sabcnews/article-42", message)
        self.assertIn("Verified article body text.", message)

    async def test_03_named_publisher_unavailable_is_reported(self) -> None:
        calls = []

        async def browser(query: str, max_results: int = 10) -> list[dict[str, str]]:
            calls.append(query)
            if "site:unavailable-example.org" in query:
                return []
            return [
                {
                    "title": "Reuters report",
                    "url": "https://www.reuters.com/world/report",
                    "snippet": "Independent reporting.",
                }
            ]

        free = {
            "provider": "duckduckgo",
            "results": [
                {
                    "title": "Reuters report",
                    "url": "https://www.reuters.com/world/report",
                    "description": "Independent reporting.",
                }
            ],
        }
        evidence = await self.collect(
            "Latest news from unavailable-example.org",
            {"provider": "wikipedia", "results": []},
            AsyncMock(side_effect=browser),
            free=free,
        )
        joined = " ".join(evidence.errors)
        self.assertIn("no browser results for unavailable-example.org", joined)
        self.assertIn("duckduckgo-http", evidence.provider)

    async def test_04_falls_back_to_other_credible_sources(self) -> None:
        async def browser(query: str, max_results: int = 10) -> list[dict[str, str]]:
            if "site:unavailable-example.org" in query:
                return []
            return [
                {
                    "title": "BBC report",
                    "url": "https://www.bbc.com/news/world-report",
                    "snippet": "Independent reporting.",
                }
            ]

        free = {
            "provider": "duckduckgo",
            "results": [
                {
                    "title": "BBC report",
                    "url": "https://www.bbc.com/news/world-report",
                    "description": "Independent reporting.",
                }
            ],
        }
        evidence = await self.collect(
            "Breaking news from unavailable-example.org",
            {"provider": "wikipedia", "results": []},
            AsyncMock(side_effect=browser),
            free=free,
        )
        # codeql[py/incomplete-url-substring-sanitization] test assertion on trusted fixture URLs.
        self.assertTrue(any("bbc.com" in item["url"] for item in evidence.results))

    async def test_05_current_technology_question_uses_live_web_retrieval(self) -> None:
        calls = []

        async def browser(query: str, max_results: int = 10) -> list[dict[str, str]]:
            calls.append(query)
            return [
                {
                    "title": "New model release",
                    "url": "https://example-tech.org/releases/new-model",
                    "snippet": "Release notes.",
                }
            ]

        free = {
            "provider": "duckduckgo",
            "results": [
                {
                    "title": "New model release",
                    "url": "https://example-tech.org/releases/new-model",
                    "description": "Release notes.",
                }
            ],
        }
        evidence = await self.collect(
            "What is the latest AI model release?",
            {"provider": "wikipedia", "results": []},
            AsyncMock(side_effect=browser),
            free=free,
        )
        self.assertIn("duckduckgo-http", evidence.provider)
        self.assertTrue(evidence.results)

    async def test_06_arbitrary_user_url_becomes_preferred_source(self) -> None:
        calls = []

        async def browser(query: str, max_results: int = 10) -> list[dict[str, str]]:
            calls.append(query)
            if "site:example.org" in query:
                return [
                    {
                        "title": "Submitted page",
                        "url": "https://example.org/report",
                        "snippet": "Page contents.",
                    }
                ]
            return []

        official = {
            "text": "Submitted page contents.",
            "links": [
                {
                    "text": "Submitted page report",
                    "url": "https://example.org/report",
                }
            ],
        }
        evidence = await self.collect(
            "Read https://example.org/report for me",
            {"provider": "wikipedia", "results": []},
            AsyncMock(side_effect=browser),
            official=official,
        )
        self.assertIn("official-site", evidence.provider)
        self.assertEqual(evidence.results[0]["source"], "example.org")

    async def test_07_historical_question_does_not_trigger_browsing(self) -> None:
        self.assertFalse(
            SearchTriggerClassifier().classify("Who founded the BBC?").needs_search
        )
        request = models.ChatRequest(
            messages=[
                models.ChatMessage(role="user", content="Who founded the BBC?")
            ]
        )
        status = SimpleNamespace(mode="ollama", model=settings.iam_primary_model)
        with (
            patch.object(
                models,
                "assemble_context",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        as_system_message=lambda: None,
                        knowledge_message=lambda: None,
                    )
                ),
            ),
            patch.object(
                models,
                "collect_live_evidence",
                new=AsyncMock(side_effect=AssertionError("must not browse")),
            ) as mocked,
        ):
            await models._prepare_messages(request, SimpleNamespace(), status)
        mocked.assert_not_awaited()

    async def test_08_browser_failure_never_fabricates_citations(self) -> None:
        evidence = await self.collect(
            "Breaking news from SABC News",
            {
                "provider": "wikipedia",
                "results": [
                    {
                        "title": "Wikipedia article",
                        "url": "https://en.wikipedia.org/wiki/SABC",
                        "description": "Background, not current news.",
                    }
                ],
            },
            AsyncMock(side_effect=RuntimeError("browser unavailable")),
        )
        message = evidence.as_system_message()
        self.assertEqual(evidence.results, [])
        self.assertIn("No live evidence was retrieved", message)
        self.assertNotIn("en.wikipedia.org", message)
        self.assertNotIn("sabcnews.com/story", message)
        self.assertIn("browser search unavailable", message)


if __name__ == "__main__":
    unittest.main()
