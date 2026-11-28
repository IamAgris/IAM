"""Playwright engine compatibility check (Doc 29 external evidence).

Runs inside the backend container, where the Playwright browser binaries live.
Prints IAM_BROWSER_COMPAT_OK only when all three engines navigate and read the
same public page. Never sends credentials or interacts with private services.

    docker compose exec -T backend python scripts/browser_compatibility_check.py
"""

from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright

TARGET = "https://example.com"
EXPECTED = "domain"


async def main() -> int:
    results = []
    async with async_playwright() as playwright:
        for name in ("chromium", "firefox", "webkit"):
            engine = getattr(playwright, name)
            browser = None
            try:
                browser = await engine.launch(headless=True)
                page = await browser.new_page()
                response = await page.goto(TARGET, wait_until="domcontentloaded", timeout=30_000)
                text = str(await page.evaluate("() => document.body.innerText"))
                ok = bool(response and response.ok and EXPECTED in text.lower())
                results.append((name, ok, f"status={response.status if response else 'none'}"))
            except Exception as exc:
                results.append((name, False, type(exc).__name__))
            finally:
                if browser is not None:
                    await browser.close()

    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    if all(ok for _, ok, _ in results):
        print("IAM_BROWSER_COMPAT_OK")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
