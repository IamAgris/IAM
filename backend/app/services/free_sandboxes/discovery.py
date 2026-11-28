"""OEDIE provider discovery for legitimate free platforms (Doc 22 §3.4).

Discovery is deliberately conservative: it only evaluates an explicit seed
list of official documentation URLs. A candidate is recorded only when the
official page responds and contains free-tier evidence. No service is invented
from search snippets and no account is created here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.services.free_sandboxes.base import SandboxCapability


@dataclass(frozen=True)
class DiscoverySeed:
    name: str
    terms_url: str
    capabilities: frozenset  # type: ignore[type-arg]
    free_markers: tuple  # type: ignore[type-arg]
    headless: bool = True


SEEDS: tuple = (  # type: ignore[type-arg]
    DiscoverySeed(
        "github_codespaces",
        "https://docs.github.com/en/billing/concepts/product-billing/github-codespaces",
        frozenset({SandboxCapability.DEVELOPMENT}),
        ("free", "included", "quota"),
    ),
    DiscoverySeed(
        "kaggle",
        "https://www.kaggle.com/docs/efficient-gpu-usage",
        frozenset({SandboxCapability.NOTEBOOK, SandboxCapability.MODEL_EVALUATION}),
        ("free", "quota"),
    ),
    DiscoverySeed(
        "huggingface",
        "https://huggingface.co/docs/hub/en/spaces-overview",
        frozenset({SandboxCapability.MODEL_EVALUATION, SandboxCapability.INFERENCE}),
        ("free", "static spaces"),
    ),
    DiscoverySeed(
        "google_colab",
        "https://research.google.com/colaboratory/faq.html",
        frozenset({SandboxCapability.NOTEBOOK}),
        ("free", "gpu"),
    ),
    DiscoverySeed(
        "stackblitz",
        "https://developer.stackblitz.com/guides/integration/create-with-sdk",
        frozenset({SandboxCapability.WEB_PROTOTYPE}),
        ("free", "sdk"),
        headless=False,
    ),
)


@dataclass
class DiscoveredProvider:
    name: str
    terms_url: str
    capabilities: List[str]
    headless: bool
    evidence: str
    verified_at: str
    registration_status: str = "candidate"


class ProviderDiscovery:
    def __init__(self, seeds: Optional[List[DiscoverySeed]] = None, timeout: float = 15.0):
        self.seeds = list(seeds or SEEDS)
        self.timeout = timeout

    async def discover(self) -> List[DiscoveredProvider]:
        found: List[DiscoveredProvider] = []
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for seed in self.seeds:
                try:
                    response = await client.get(seed.terms_url)
                except httpx.HTTPError:
                    continue
                if response.status_code != 200:
                    continue
                text = response.text.lower()
                evidence = [m for m in seed.free_markers if m in text]
                if not evidence:
                    continue
                found.append(
                    DiscoveredProvider(
                        name=seed.name,
                        terms_url=seed.terms_url,
                        capabilities=sorted(c.value for c in seed.capabilities),
                        headless=seed.headless,
                        evidence=", ".join(evidence),
                        verified_at=datetime.now(timezone.utc).isoformat(),
                    )
                )
        return found

    def to_records(self, discovered: List[DiscoveredProvider]) -> List[Dict[str, Any]]:
        return [
            {
                "name": item.name,
                "provider_type": item.name,
                "capabilities": item.capabilities,
                "terms_url": item.terms_url,
                "headless": item.headless,
                "registration_status": item.registration_status,
                "evidence": item.evidence,
                "docs_verified_at": item.verified_at,
            }
            for item in discovered
        ]
