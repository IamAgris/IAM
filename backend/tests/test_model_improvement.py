"""OD-52 Phase H: proposals are evidence only; no promotion or training."""

import unittest
import uuid

from app.models.modelrouter import DiscoveredModel
from app.services.model_improvement import ModelImprovementService


class FakeResult:
    def __init__(self, rows):
        self.rows = list(rows)

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeDB:
    def __init__(self, rows):
        self.rows = rows

    async def execute(self, statement):
        return FakeResult(self.rows)


class ModelImprovementTests(unittest.IsolatedAsyncioTestCase):
    async def test_proposal_is_evidence_only(self):
        row = DiscoveredModel(
            id=uuid.uuid4(),
            provider_id=uuid.uuid4(),
            model_id="nvidia/code",
            alias="nv-code",
            capabilities=["coding"],
            access_type="free",
            endpoint_status="available",
        )
        proposals = await ModelImprovementService(FakeDB([row])).proposals()
        self.assertTrue(proposals)
        for item in proposals:
            self.assertEqual(item["claim"], "proposal only")
            self.assertFalse(item["promotion_performed"])
            self.assertFalse(item["training_performed"])
            self.assertTrue(item["licensing_check_required"])


if __name__ == "__main__":
    unittest.main()
