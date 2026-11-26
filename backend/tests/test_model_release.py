"""Phase 7 tests: reproducible evidence, provenance, signed approval, rollback."""

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from app.models.development import ModelEvaluation, UpgradeHistory
from app.models.security import AuditEvent
from app.services.ai_research.artifacts import ArtifactKind, FileSystemArtifactStore, artifact_key
from app.services.ai_research.benchmarks import BenchmarkResult
from app.services.ai_research.release_gate import ModelReleaseError, ModelReleaseService
from app.services.ai_research.registry import ModelRegistry


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

    async def refresh(self, _obj):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


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
                "expires_at": "2026-11-26T00:00:00+00:00",
            }

    return Approvals


def benchmark(store, filename, mean, config_hash="cfg-1"):
    result = BenchmarkResult(
        spec_name="coding",
        task_type="coding",
        model="test-model",
        experiment_id="exp-1",
        scores=[mean, mean],
        mean=mean,
        stdev=0.0,
        config_hash=config_hash,
        hardware={"cpu": "test"},
    )
    key = artifact_key("exp-1", ArtifactKind.BENCHMARK, filename)
    store.put(key, json.dumps(result.to_dict(), sort_keys=True).encode("utf-8"))
    return key


def register(service):
    return service.register(
        model="test-model",
        version="v1",
        checkpoint_ref="experiments/exp-1/checkpoint/model.safetensors",
        capability_profile={"coding": 0.7},
        baseline_score=0.60,
        min_improvement=0.05,
        dataset_ref="datasets/clean-v3",
        dataset_sha256="a" * 64,
        licence="permissive",
        consent_recorded=True,
        poisoning_scan_ref="experiments/exp-1/result/poisoning.json",
        benchmark_ref="experiments/exp-1/benchmark/first.json",
        actor="iam",
    )


class ModelReleaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = FileSystemArtifactStore(Path(self.tmp.name))
        self.db = FakeDB()
        self.service = ModelReleaseService(self.db, store=self.store)
        self.addCleanup(self.tmp.cleanup)

    async def test_promote_requires_reproducible_evidence_and_approval(self):
        await register(self.service)
        refs = [benchmark(self.store, "first.json", 0.72), benchmark(self.store, "second.json", 0.73)]
        with patch(
            "app.services.ai_research.release_gate.CreatorApprovalService", approvals()
        ):
            result = await self.service.promote("test-model", "v1", refs, "iam")
        self.assertEqual(result["status"], "deployed")
        self.assertGreaterEqual(result["score"], 0.72)
        self.assertTrue(any(isinstance(row, ModelEvaluation) for row in self.db.rows))
        self.assertTrue(any(isinstance(row, UpgradeHistory) for row in self.db.rows))
        self.assertTrue(any(row.event_type == "model_released" for row in self.db.rows if isinstance(row, AuditEvent)))

    async def test_state_survives_restart(self):
        await register(self.service)
        refs = [benchmark(self.store, "first.json", 0.72), benchmark(self.store, "second.json", 0.73)]
        with patch(
            "app.services.ai_research.release_gate.CreatorApprovalService", approvals()
        ):
            await self.service.promote("test-model", "v1", refs, "iam")
        restarted = ModelRegistry(self.store)
        self.assertEqual(restarted.hydrate(), 1)
        self.assertEqual(restarted.active("test-model"), "v1")

    async def test_no_improvement_denied(self):
        await register(self.service)
        refs = [benchmark(self.store, "first.json", 0.55), benchmark(self.store, "second.json", 0.56)]
        with patch(
            "app.services.ai_research.release_gate.CreatorApprovalService", approvals()
        ):
            with self.assertRaises(ModelReleaseError):
                await self.service.promote("test-model", "v1", refs, "iam")

    async def test_insufficient_evidence_denied(self):
        await register(self.service)
        refs = [benchmark(self.store, "first.json", 0.72)]
        with patch(
            "app.services.ai_research.release_gate.CreatorApprovalService", approvals()
        ):
            with self.assertRaises(ModelReleaseError):
                await self.service.promote("test-model", "v1", refs, "iam")

    async def test_unsigned_release_denied(self):
        await register(self.service)
        refs = [benchmark(self.store, "first.json", 0.72), benchmark(self.store, "second.json", 0.73)]
        with patch(
            "app.services.ai_research.release_gate.CreatorApprovalService", approvals(False)
        ):
            with self.assertRaises(ModelReleaseError):
                await self.service.promote("test-model", "v1", refs, "iam")

    async def test_rollback_requires_authority(self):
        await register(self.service)
        refs = [benchmark(self.store, "first.json", 0.72), benchmark(self.store, "second.json", 0.73)]
        with patch(
            "app.services.ai_research.release_gate.CreatorApprovalService", approvals()
        ):
            await self.service.promote("test-model", "v1", refs, "iam")
            result = await self.service.rollback("test-model", "v1", "regression", "iam")
        self.assertEqual(result["status"], "deployed")
        self.assertTrue(any(row.status == "rolled_back" for row in self.db.rows if isinstance(row, UpgradeHistory)))


if __name__ == "__main__":
    unittest.main()
