"""Real-database cache, TTL and IICS evidence tests (aiosqlite, no mocks)."""

import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.iics import IICSClaim, IICSSource
from app.models.live_evidence import LiveEvidenceCache
from app.services.live_evidence_cache import (
    annotate_reputation,
    get_cached,
    store_cached,
)
from app.services.live_information_policy import (
    LiveEvidence,
    ResearchDepth,
    SearchTrigger,
)

QUERY = "What's the latest SABC news?"


class RealDbCacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(LiveEvidenceCache.__table__.create)
            await connection.run_sync(IICSSource.__table__.create)
            await connection.run_sync(IICSClaim.__table__.create)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    def evidence(self) -> LiveEvidence:
        return LiveEvidence(
            query=QUERY,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            provider="official-site",
            results=[
                {
                    "title": "SABC reports new development",
                    "url": "https://www.sabcnews.com/sabcnews/new-development/",
                    "description": "Article text.",
                    "published": "27 November 2026",
                    "source": "sabcnews.com",
                    "claim_label": "single_source",
                    "confidence": 0.45,
                }
            ],
            errors=[],
            analysis={},
        )

    async def test_store_then_hit_reuses_valid_cache(self) -> None:
        trigger = SearchTrigger(True, ("latest_news",), ("sabcnews.com",), ResearchDepth.STANDARD)
        async with self.sessions() as db:
            await store_cached(db, self.evidence(), trigger)
        async with self.sessions() as db:
            cached = await get_cached(db, QUERY)
        self.assertIsNotNone(cached)
        self.assertIn("+cache", cached.provider)  # type: ignore[union-attr]
        self.assertEqual(len(cached.results), 1)  # type: ignore[union-attr]

    async def test_expired_cache_is_not_reused(self) -> None:
        trigger = SearchTrigger(True, ("latest_news",), (), ResearchDepth.QUICK)
        async with self.sessions() as db:
            await store_cached(db, self.evidence(), trigger)
            await db.execute(
                update(LiveEvidenceCache).values(
                    expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)
                )
            )
            await db.commit()
        async with self.sessions() as db:
            self.assertIsNone(await get_cached(db, QUERY))

    async def test_sources_and_claims_are_registered_in_iics(self) -> None:
        trigger = SearchTrigger(True, ("latest_news",), ("sabcnews.com",), ResearchDepth.STANDARD)
        async with self.sessions() as db:
            await store_cached(db, self.evidence(), trigger)
            sources = (await db.execute(select(IICSSource))).scalars().all()
            claims = (await db.execute(select(IICSClaim))).scalars().all()
        self.assertEqual(len(sources), 1)
        self.assertIn("sabcnews.com", sources[0].domain)
        self.assertEqual(sources[0].freshness_class, "volatile")
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].label, "provisional")

    async def test_reputation_is_read_from_registered_source(self) -> None:
        trigger = SearchTrigger(True, ("latest_news",), ("sabcnews.com",), ResearchDepth.STANDARD)
        evidence = self.evidence()
        async with self.sessions() as db:
            await store_cached(db, evidence, trigger)
            enriched = await annotate_reputation(db, [dict(item) for item in evidence.results])
        self.assertGreater(enriched[0]["reliability"], 0.0)
        self.assertEqual(enriched[0]["source_freshness_class"], "volatile")


if __name__ == "__main__":
    unittest.main()
