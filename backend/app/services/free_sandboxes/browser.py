"""Interactive browser opener for browser-mediated providers (Doc 22 §3.7).

StackBlitz projects are created by opening a project link in a real browser;
there is no headless server API for that operation. This opener is opt-in and
never executes content returned by the page.
"""

from __future__ import annotations

from typing import Any


class PlaywrightBrowserOpener:
    def __init__(self, headless: bool = False, timeout_ms: int = 30_000) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms

    def __call__(self, url: str) -> str:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self.headless)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                return page.title()
            finally:
                browser.close()

    def describe(self) -> Any:
        return {"type": "playwright", "headless": self.headless}
