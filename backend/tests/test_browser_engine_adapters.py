"""Tests for the UWAIE browser engine adapter registry (Doc 29 WP-01)."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.core.config import settings
from app.services.browser_engine_adapters import (
    BrowserEngineUnavailable,
    available_engines,
    get_adapter,
)
from app.services.browser_service import BrowserService


class FakeContext:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class FakeBrowser:
    async def new_context(self, **kwargs):
        return FakeContext()


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.browser = BrowserService()
        self.browser._browser = FakeBrowser()

        async def noop():
            return None

        self.browser._ensure_browser = noop

    def test_sessions_get_separate_contexts(self):
        async def run():
            first = await self.browser.open_session("a")
            second = await self.browser.open_session("b")
            self.assertIsNot(self.browser._contexts["a"], self.browser._contexts["b"])
            self.assertEqual(first["actor_type"], "agent")
            self.assertTrue(await self.browser.close_session("a"))
            self.assertNotIn("a", self.browser._contexts)
            self.assertTrue(self.browser._contexts["b"].closed is False)

        asyncio.run(run())

    def test_visible_mode_fails_closed(self):
        with patch.object(settings, "browser_visible_mode_enabled", False):
            with self.assertRaises(BrowserEngineUnavailable):
                asyncio.run(self.browser.open_session("v", mode="visible"))

    def test_concurrency_cap(self):
        with patch.object(settings, "browser_max_concurrent_sessions", 1):
            async def run():
                await self.browser.open_session("one")
                with self.assertRaises(BrowserEngineUnavailable):
                    await self.browser.open_session("two")

            asyncio.run(run())


class AdapterTests(unittest.TestCase):
    def test_registry_selects_adapter(self):
        self.assertEqual(get_adapter("chromium").name, "chromium")
        self.assertIn("screenshots", get_adapter("chromium").capabilities())

    def test_unsupported_engine_is_denied(self):
        with self.assertRaises(BrowserEngineUnavailable):
            get_adapter("opera")

    def test_missing_runtime_fails_closed(self):
        playwright = SimpleNamespace(chromium=object())
        engines = available_engines(playwright)
        self.assertIn("chromium", engines)
        self.assertNotIn("firefox", engines)
        with self.assertRaises(BrowserEngineUnavailable):
            get_adapter("firefox").engine(playwright)

    def test_browser_can_be_disabled_by_policy(self):
        with patch.object(settings, "browser_enabled", False):
            with self.assertRaises(BrowserEngineUnavailable):
                BrowserService()


if __name__ == "__main__":
    unittest.main()
