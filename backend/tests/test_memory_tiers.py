"""Memory items carry an epistemic tier alongside the flat memory type."""

import unittest
from unittest.mock import AsyncMock, patch

from app.services.memory_service import MEMORY_TIERS, MemoryService


class FakeResult:
    def scalar_one_or_none(self):
        return None


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    async def execute(self, statement):
        return FakeResult()

    async def flush(self):
        return None

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        return None


class MemoryTierTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_tier_is_rejected_before_storage(self):
        service = MemoryService(FakeDB())
        with self.assertRaisesRegex(ValueError, "invalid memory tier"):
            await service.store_memory(
                "test", source="test", tier="not_a_tier"
            )

    async def test_valid_tier_is_persisted(self):
        service = MemoryService(FakeDB())
        with patch.object(service, "_generate_embedding", AsyncMock(return_value=None)):
            result = await service.store_memory(
                "test", source="test", tier="semantic"
            )
        self.assertEqual(result["tier"], "semantic")
        self.assertEqual(MemoryTierTests._tier_of(service), "semantic")

    @staticmethod
    def _tier_of(service):
        return service.db.added[0].tier

    def test_all_seven_tiers_are_declared(self):
        self.assertEqual(len(MEMORY_TIERS), 7)
        self.assertIn("strategic", MEMORY_TIERS)


if __name__ == "__main__":
    unittest.main()
