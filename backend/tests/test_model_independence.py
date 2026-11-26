"""Model independence tests: portable export, scored comparisons, signed gates."""

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.models.modelindependence import ModelComparison
from app.services.ai_research.artifacts import FileSystemArtifactStore
from app.services.model_independence import (
    ModelIndependenceError,
    ModelIndependenceService,
    weighted_score,
)
from app.services.vision_service import VisionService


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self):
        self.rows = []

    def add(self, obj):
        if obj not in self.rows:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.rows.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        rows = [row for row in self.rows if isinstance(row, entity)]
        return FakeResult(rows)


def approvals(authorized=True):
    class Approvals:
        def __init__(self, _db):
            pass

        async def check_authorization(self, _action, target_ref=None):
            if not authorized:
                return {"authorized": False, "reason": "no signed authorization"}
            return {
                "authorized": True,
                "authorization_id": str(uuid.uuid4()),
                "signer_id": "creator-signer",
                "target_ref": target_ref,
            }

    return Approvals


class ScoringTests(unittest.TestCase):
    def test_weights_sum_to_one(self):
        self.assertEqual(weighted_score({key: 1.0 for key in (
            "coding_correctness", "repository_engineering", "autonomous_tool_use",
            "reasoning", "security", "hardware_efficiency", "reliability",
        )}), 1.0)

    def test_missing_criteria_are_zero_not_assumed(self):
        self.assertLess(weighted_score({"coding_correctness": 0.5}), 0.2)

    def test_vision_model_is_replaceable(self):
        with patch.object(settings, "vision_model", "other-vision-model"):
            self.assertEqual(VisionService().model, "other-vision-model")


class IndependenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = FileSystemArtifactStore(Path(self.tmp.name))
        self.db = FakeDB()
        self.service = ModelIndependenceService(self.db, store=self.store)
        self.addCleanup(self.tmp.cleanup)

    async def test_comparison_scored_and_signed_adoption(self):
        scores = {
            "coding_correctness": 0.9,
            "repository_engineering": 0.8,
            "autonomous_tool_use": 0.7,
            "reasoning": 0.8,
            "security": 0.9,
            "hardware_efficiency": 0.6,
            "reliability": 0.7,
        }
        entry = await self.service.record_comparison(
            model_name="candidate", provider="local", model_id="qwen-coder",
            capabilities_tested=["coding"], scores=scores, actor="iam",
        )
        self.assertAlmostEqual(entry["overall_score"], 0.8, places=3)
        with patch(
            "app.services.model_independence.CreatorApprovalService", approvals()
        ):
            adopted = await self.service.adopt(entry["id"], "iam")
        self.assertTrue(adopted["is_adopted"])

    async def test_adoption_denied_without_authority(self):
        entry = await self.service.record_comparison(
            model_name="candidate", provider="local", model_id="qwen-coder",
            capabilities_tested=[], scores={}, actor="iam",
        )
        with patch(
            "app.services.model_independence.CreatorApprovalService", approvals(False)
        ):
            with self.assertRaises(ModelIndependenceError):
                await self.service.adopt(entry["id"], "iam")

    async def test_portable_export_excludes_private_content(self):
        exported = await self.service.export(["identity", "goals", "skills"], "iam")
        self.assertFalse(exported["private_content"])
        payload = json.loads(self.store.get(exported["location"]).decode("utf-8"))
        self.assertTrue(payload["model_independent"])
        self.assertIn("memory", payload)
        self.assertNotIn("messages", json.dumps(payload).lower())
        self.assertNotIn("conversation", json.dumps(payload).lower())

    async def test_fallback_requires_signed_authority(self):
        with patch(
            "app.services.model_independence.CreatorApprovalService", approvals(False)
        ):
            with self.assertRaises(ModelIndependenceError):
                await self.service.set_fallback("primary", "backup", "ollama", "iam")
        with patch(
            "app.services.model_independence.CreatorApprovalService", approvals()
        ):
            row = await self.service.set_fallback("primary", "backup", "ollama", "iam")
        self.assertTrue(row["is_active"])
        self.assertEqual((await self.service.active_fallback())["fallback_model"], "backup")


if __name__ == "__main__":
    unittest.main()
