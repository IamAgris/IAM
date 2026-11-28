"""Best-effort Google/Brave public-page adapters: parse results, detect blocks."""

import unittest
from unittest.mock import AsyncMock, patch

from app.services.search_service import SearchService, search_service


class FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


class FakeClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def get(self, *_args, **_kwargs):
        return self.response


class PublicSearchProviderTests(unittest.TestCase):
    def setUp(self):
        self.service = SearchService()

    def test_bot_protection_is_detected(self):
        self.assertIn("429", self.service._public_page_blocked(429, "<html></html>"))
        blocked = "<title>Google - Captcha</title>"
        self.assertIn("bot", self.service._public_page_blocked(200, blocked))
        self.assertEqual(self.service._public_page_blocked(200, "<title>Results</title>"), "")

    def test_parser_extracts_google_and_brave_style_links(self):
        page = """
        <a href="/url?q=https%3A%2F%2Fwww.reuters.com%2Fworld%2Fstory&amp;sa=U">Reuters story</a>
        <a href="https://www.bbc.com/news/article">BBC <b>report</b></a>
        <a href="https://www.google.com/settings">Google settings</a>
        <a href="/url?q=https%3A%2F%2Fwww.reuters.com%2Fworld%2Fstory">Reuters duplicate</a>
        """
        results = self.service._parse_public_anchors(
            page, 5, ("google.", "brave.com", "duckduckgo.", "search.")
        )
        urls = [item["url"] for item in results]
        self.assertEqual(
            urls,
            ["https://www.reuters.com/world/story", "https://www.bbc.com/news/article"],
        )
        self.assertEqual(results[1]["title"], "BBC report")


class NewsRssTests(unittest.IsolatedAsyncioTestCase):
    async def test_rss_items_become_sources_with_dates(self):
        page = """<?xml version="1.0"?><rss><channel>
          <item><title>Story one</title><link>https://news.example.org/a</link>
          <pubDate>Fri, 27 Nov 2026 19:00:00 GMT</pubDate>
          <source url="https://publisher.example.org">Publisher</source></item>
        </channel></rss>"""
        response = FakeResponse(200, page)
        with patch(
            "app.services.search_service.httpx.AsyncClient",
            side_effect=lambda **_kwargs: FakeClient(response),
        ):
            outcome = await search_service._search_google_news_rss("q", 3)
        self.assertEqual(outcome["provider"], "google-news-rss")
        self.assertEqual(outcome["results"][0]["url"], "https://news.example.org/a")
        self.assertEqual(outcome["results"][0]["source"], "publisher.example.org")
        self.assertIn("27 Nov 2026", outcome["results"][0]["published"])

    async def test_rss_dispatch(self):
        payload = {"provider": "rss", "results": []}
        with patch.object(
            search_service, "_search_google_news_rss", new=AsyncMock(return_value=payload)
        ) as google, patch.object(
            search_service, "_search_bing_news_rss", new=AsyncMock(return_value=payload)
        ) as bing:
            await search_service.search("q", provider="google-news-rss")
            await search_service.search("q", provider="bing-news-rss")
        google.assert_awaited_once()
        bing.assert_awaited_once()


class PublicSearchDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_google_and_brave_html_are_dispatched(self):
        payload = {"provider": "public", "results": []}
        with patch.object(
            search_service, "_search_google_html", new=AsyncMock(return_value=payload)
        ) as google, patch.object(
            search_service, "_search_brave_html", new=AsyncMock(return_value=payload)
        ) as brave:
            await search_service.search("q", provider="google-html")
            await search_service.search("q", provider="brave-html")
        google.assert_awaited_once()
        brave.assert_awaited_once()

    async def test_blocked_page_returns_no_results(self):
        response = FakeResponse(429, "<html>rate limited</html>")
        with patch(
            "app.services.search_service.httpx.AsyncClient",
            side_effect=lambda **_kwargs: FakeClient(response),
        ):
            outcome = await search_service._search_google_html("q", 3)
        self.assertEqual(outcome["provider"], "google-html")
        self.assertEqual(outcome["results"], [])
        self.assertIn("429", outcome["error"])

    async def test_successful_page_returns_parsed_results(self):
        page = '<a href="https://example.org/a">Example result</a>'
        response = FakeResponse(200, page)
        with patch(
            "app.services.search_service.httpx.AsyncClient",
            side_effect=lambda **_kwargs: FakeClient(response),
        ):
            outcome = await search_service._search_brave_html("q", 3)
        self.assertEqual(outcome["results"][0]["url"], "https://example.org/a")
        self.assertIsNone(outcome.get("error"))


if __name__ == "__main__":
    unittest.main()
