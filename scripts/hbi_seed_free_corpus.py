"""Seed IAM HBI with free/open research metadata and synthetic scenarios.

No paid API, no private corpus, no human participants. Every ingested item goes
through the normal HBI corpus gate and stays metadata-only until per-item
rights are checked. Synthetic scenarios are explicitly hypotheses, not evidence.

Usage:
    IAM_API_KEY=<admin key> IAM_API_URL=http://localhost:8000 python scripts/hbi_seed_free_corpus.py
"""

from __future__ import annotations

import json
import os
import sys

import httpx

ADAPTERS = ("wikidata", "openalex", "crossref")
QUERY = os.environ.get("IAM_HBI_SEED_QUERY", "human behaviour cooperation trust")
STUDY_REF = os.environ.get("IAM_HBI_STUDY_REF", "free-synthetic-2026-11-28")


def main() -> int:
    endpoint = os.environ.get("IAM_API_URL", "http://localhost:8000").rstrip("/")
    token = os.environ.get("IAM_API_KEY", "")
    if not token:
        print("IAM_API_KEY is required", file=sys.stderr)
        return 2
    headers = {"X-API-Key": token}

    try:
        with httpx.Client(base_url=endpoint, headers=headers, timeout=60) as client:
            sources = client.get("/api/v1/hbi/research/open-sources")
            sources.raise_for_status()
            print(f"free adapters available: {sources.json().get('count')}")

            for adapter in ADAPTERS:
                response = client.post(
                    "/api/v1/hbi/research/open-sources/ingest",
                    json={"adapter": adapter, "query": QUERY, "limit": 5},
                )
                response.raise_for_status()
                data = response.json()
                print(f"{adapter}: {data.get('documents', 0)} documents ({data.get('terms', '')})")

            synthetic = client.post(
                "/api/v1/hbi/research/lab/synthetic",
                json={"study_ref": STUDY_REF, "count": 10, "purpose": "research"},
            )
            synthetic.raise_for_status()
            print(f"synthetic scenarios: {synthetic.json().get('count', 0)}")
            print(json.dumps(sources.json(), indent=2)[:400])
    except httpx.HTTPError as exc:
        print(f"HBI seed failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
