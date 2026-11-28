"""Memory consolidation is scheduled and never silently merges duplicates."""

import unittest
from unittest.mock import AsyncMock, patch

from app.services.memory_service import MemoryService
from app.workers.arq_model_catalog import (
    WorkerSettings,
    run_memory_consolidation,
)


class FakeDB:
    pass


class MemoryLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_consolidation_expires_and_links_conflicts_only(self):
        service = MemoryService(FakeDB())
        duplicates = [
            (
                {"id": "a", "verification_status": "verified"},
                {"id": "b", "verification_status": "disputed"},
                0.91,
            ),
            (
                {"id": "c", "verification_status": "unverified"},
                {"id": "d", "verification_status": "unverified"},
                0.95,
            ),
        ]
        with (
            patch.object(service, "expire_memories", AsyncMock(return_value=2)),
            patch.object(service, "find_duplicate_memories", AsyncMock(return_value=duplicates)),
            patch.object(service, "create_memory_relationship", AsyncMock()) as link,
        ):
            result = await service.consolidate_memories(dry_run=False)
        self.assertEqual(result["expired_count"], 2)
        self.assertEqual(result["duplicate_pairs_found"], 2)
        self.assertEqual(result["contradiction_links_created"], 1)
        link.assert_awaited_once_with("a", "b", "contradicts", strength=0.8)

    async def test_dry_run_does_not_mutate(self):
        service = MemoryService(FakeDB())
        with (
            patch.object(service, "expire_memories", AsyncMock()) as expire,
            patch.object(
                service, "find_duplicate_memories", AsyncMock(return_value=[])
            ),
        ):
            result = await service.consolidate_memories(dry_run=True)
        expire.assert_not_awaited()
        self.assertTrue(result["dry_run"])

    def test_cron_is_registered(self):
        self.assertIn(run_memory_consolidation, WorkerSettings.functions)
        self.assertEqual(len(WorkerSettings.cron_jobs), 3)


if __name__ == "__main__":
    unittest.main()
