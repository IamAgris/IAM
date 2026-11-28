"""Research workflow must degrade gracefully when a free provider stalls."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.research_service import ResearchService


class FakeResult:
    def scalar_one_or_none(self):
        return None

    def scalars(self):
        class _S:
            def all(self):
                return []

        return _S()


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0

    async def execute(self, statement):
        return FakeResult()

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1

    async def flush(self):
        return None

    async def rollback(self):
        return None


class FakeSession:
    async def __aenter__(self):
        return FakeDB()

    async def __aexit__(self, *args):
        return False


class ResearchDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_search_returns_partial_record_not_error(self):
        with patch("app.services.research_service.AsyncSessionLocal", FakeSession):
            with patch(
                "app.services.research_service.search_service.search",
                new_callable=AsyncMock,
                side_effect=TimeoutError("provider stalled"),
            ):
                result = await ResearchService().research_topic(
                    "deadline test", store_as_memory=False, max_results=3
                )
        self.assertEqual(result["query"], "deadline test")
        self.assertEqual(result["sources"], [])
        self.assertIn("findings", result)

    async def test_search_is_bounded_by_configured_deadline(self):
        slow = AsyncMock(side_effect=lambda **kw: asyncio.sleep(5))
        with patch("app.services.research_service.AsyncSessionLocal", FakeSession):
            with patch("app.services.research_service.search_service.search", slow):
                with patch.object(settings, "research_workflow_timeout_seconds", 0.05):
                    result = await ResearchService().research_topic(
                        "slow provider", store_as_memory=False, max_results=3
                    )
        self.assertEqual(result["sources"], [])


if __name__ == "__main__":
    unittest.main()
