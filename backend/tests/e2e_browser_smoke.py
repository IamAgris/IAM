"""Opt-in real Playwright smoke against a public site.

    IAM_BROWSER_E2E=1 python tests/e2e_browser_smoke.py

Skipped by default. Uses the real browser stack, never invented page content.
No credentials are used and no private data is sent.
"""

import asyncio
import json
import os
import sys

from app.services.browser_service import BrowserService

URL = os.environ.get("IAM_BROWSER_E2E_URL", "https://example.com")


async def main() -> None:
    service = BrowserService()
    try:
        result = await service.fetch_page(URL)
        summary = {
            "url": result.get("url") or URL,
            "title": str(result.get("title") or "")[:200],
            "text_excerpt": str(result.get("text") or "")[:300],
            "success": bool(result.get("success", True)),
        }
        print(json.dumps(summary, ensure_ascii=False))
        if not summary["success"]:
            raise SystemExit(1)
    finally:
        await service.stop()


if __name__ == "__main__":
    if os.environ.get("IAM_BROWSER_E2E") != "1":
        print("SKIPPED: set IAM_BROWSER_E2E=1 to run the live browser smoke test")
        sys.exit(0)
    asyncio.run(main())
