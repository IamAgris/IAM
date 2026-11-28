"""Free official sources may supply IPLCI evidence, never legal verification."""

import unittest
from unittest.mock import AsyncMock

from app.services.iplci.free_evidence import (
    FREE_OFFICIAL_SOURCES,
    seed_payloads,
    seed_validation_evidence,
)


class FakeService:
    def __init__(self):
        self.opened = []
        self.evidence = []
        self.verify = AsyncMock()
        self.counter = 0

    async def open_validation_task(self, payload, actor="sdk"):
        self.counter += 1
        self.opened.append(payload)
        return {"id": f"task-{self.counter}"}

    async def record_validation_evidence(self, task_id, payload, actor="sdk"):
        self.evidence.append((task_id, payload))
        return {"id": task_id, "status": "in_review"}


class FreeEvidenceTests(unittest.IsolatedAsyncioTestCase):
    def test_sources_are_official_https_pages(self):
        self.assertGreaterEqual(len(FREE_OFFICIAL_SOURCES), 8)
        for item in FREE_OFFICIAL_SOURCES:
            self.assertTrue(item["url"].startswith("https://"))

    def test_payloads_carry_evidence_and_no_verification(self):
        for payload in seed_payloads():
            self.assertIn("evidence", payload)
            self.assertEqual(payload["official_source_url"], payload["evidence"])

    async def test_seeding_never_calls_verify(self):
        service = FakeService()
        result = await seed_validation_evidence(service)
        self.assertEqual(result["created"], len(FREE_OFFICIAL_SOURCES))
        self.assertEqual(len(service.evidence), len(FREE_OFFICIAL_SOURCES))
        service.verify.assert_not_awaited()
        self.assertTrue(all(t["status"] == "in_review" for t in result["tasks"]))


if __name__ == "__main__":
    unittest.main()
