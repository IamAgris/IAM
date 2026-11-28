"""Seed the Doc 25 §18 provider catalogue into the local registry.

Usage:  python scripts/seed_provider_registry.py

Idempotent. Records candidate names, categories and unreviewed gates only.
No network call, credential, adapter enablement or real-money authority is
created. Run Alembic migrations before seeding.
"""

import asyncio
import sys

from app.core.database import AsyncSessionLocal
from app.services.financial_intelligence.provider_registry import ProviderRegistryService


async def main() -> int:
    async with AsyncSessionLocal() as db:
        result = await ProviderRegistryService(db).seed_candidates("system")
    print(
        f"candidates={result['candidates']} created={result['created']} "
        f"existing={result['existing']} adapters_disabled="
        f"{str(result['all_adapters_disabled']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
