"""Opt-in real-web smoke for conditional live-information escalation.

    IAM_LIVE_E2E=1 python tests/e2e_live_information_smoke.py

Skipped by default. Uses the real Playwright browser stack and no search API
key: the configured provider is simulated as an unsuitable Wikipedia fallback,
so the only way to obtain evidence is the conditional browser escalation.
No credentials are used and no private data is sent. The output is evidence,
not a claim — if retrieval fails the process exits non-zero and prints why.
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.browser_service import browser_service
from app.services.live_information_policy import collect_live_evidence
from app.services.search_service import search_service

QUERY = os.environ.get(
    "IAM_LIVE_E2E_QUERY", "What's the latest news from SABC?"
)
MAX_RESULTS = int(os.environ.get("IAM_LIVE_E2E_MAX_RESULTS", "3"))
TIMEOUT = float(os.environ.get("IAM_LIVE_E2E_TIMEOUT", "60"))


async def main() -> None:
    # A Wikipedia result is deliberately supplied so the smoke proves it is
    # rejected as live evidence rather than silently used.
    unsuitable = {
        "query": QUERY,
        "provider": "wikipedia",
        "results": [
            {
                "title": "SABC (background)",
                "url": "https://en.wikipedia.org/wiki/SABC",
                "description": "Encyclopaedia background, not current news.",
            }
        ],
    }
    try:
        with (
            patch.object(
                search_service, "search", new=AsyncMock(return_value=unsuitable)
            ),
            patch.object(settings, "iam_live_info_use_browser", False),
            patch.object(settings, "iam_live_info_escalate_to_browser", True),
            patch.object(settings, "iam_live_info_timeout_seconds", TIMEOUT),
        ):
            evidence = await collect_live_evidence(
                QUERY, max_results=MAX_RESULTS, timeout=TIMEOUT
            )

        summary = {
            "query": QUERY,
            "retrieved_at": evidence.retrieved_at,
            "provider": evidence.provider,
            "escalation_fired": any(
                name in evidence.provider
                for name in ("official-site", "duckduckgo-browser")
            ),
            "wikipedia_rejected": all(
                "wikipedia.org" not in item["url"] for item in evidence.results
            ),
            "result_count": len(evidence.results),
            "results": evidence.results,
            "retrieval_notes": evidence.errors,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))

        if not evidence.results:
            print("FAIL: no live evidence retrieved", file=sys.stderr)
            raise SystemExit(1)
        if "SABC" in QUERY and not any(
            "sabcnews.com" in item["url"] for item in evidence.results
        ):
            print("FAIL: no SABC article retrieved", file=sys.stderr)
            raise SystemExit(2)
    finally:
        # Same event loop as the browser session — a second asyncio.run()
        # would close the Playwright transport mid-shutdown.
        try:
            await browser_service.stop()
        except Exception as exc:  # pragma: no cover - cleanup must not mask result
            print(f"cleanup note: {type(exc).__name__}", file=sys.stderr)


if __name__ == "__main__":
    if os.environ.get("IAM_LIVE_E2E") != "1":
        print("SKIPPED: set IAM_LIVE_E2E=1 to run the live retrieval smoke test")
        sys.exit(0)
    asyncio.run(main())
