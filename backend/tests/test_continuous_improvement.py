"""Phase 10 tests: wired research memory, scheduling, recovery and reflection."""

import unittest
from datetime import datetime, timezone
from uuid import uuid4

from app.models.capability import CapabilityAssessment, CapabilityDefinition
from app.models.reflection import ReflectionEntry
from app.services.ai_research.adapters import ColabResearchAdapter, KaggleResearchAdapter
from app.services.ai_research.artifacts import FileSystemArtifactStore
from app.services.ai_research.continuous_improvement import ContinuousImprovement
from app.services.ai_research.jobs import HardwareRequirement, ResearchJob, ResearchMethod
from app.services.free_sandboxes.base import EnvironmentState, SandboxError


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
                obj.id = uuid4()
            self.rows.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


class Driver:
    def __init__(self, results=None, fail_provision=False):
        self.results = results or {"status": "completed", "score": 0.9}
        self.environments = {}
        self.counter = 0
        self.fail_provision = fail_provision

    async def provision(self, request):
        if self.fail_provision:
            raise SandboxError("provider unavailable")
        self.counter += 1
        external_id = f"env-{self.counter}"
        self.environments[external_id] = EnvironmentState.PROVISIONING
        return external_id

    async def start(self, external_id):
        self.environments[external_id] = EnvironmentState.RUNNING

    async def status(self, external_id):
        return self.environments[external_id]

    async def collect(self, external_id):
        return dict(self.results)


def job(experiment_id="exp-1"):
    return ResearchJob(
        experiment_id=experiment_id,
        title="coding benchmark",
        task_type="coding",
        complexity=3,
        method=ResearchMethod.QLORA,
        model="local-qwen-3b",
        dataset_ref="datasets/coding-v1",
        hardware=HardwareRequirement(min_ram_mb=4096, max_runtime_minutes=60),
    )


class ContinuousImprovementTests(unittest.IsolatedAsyncioTestCase):
    async def test_failure_becomes_next_plan_input_and_reflection(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = FileSystemArtifactStore(tmp)
            failed_driver = Driver({"status": "failed", "reason": "checkpoint missing", "score": 0})
            first = await ContinuousImprovement(
                FakeDB(), store=store, adapters=[ColabResearchAdapter(driver=failed_driver)]
            ).run(job("exp-fail"), "iam")
            self.assertEqual(first.status, "failed")
            self.assertIn("checkpoint", first.diagnosis)

            second = await ContinuousImprovement(
                FakeDB(),
                store=store,
                adapters=[ColabResearchAdapter(driver=Driver())],
            ).run(job("exp-next"), "iam")
            self.assertIn("exp-fail", second.prior_failures)
            self.assertEqual(second.status, "completed")

    async def test_recovery_switches_provider(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            store = FileSystemArtifactStore(tmp)
            result = await ContinuousImprovement(
                FakeDB(),
                store=store,
                adapters=[
                    ColabResearchAdapter(driver=Driver(fail_provision=True)),
                    KaggleResearchAdapter(driver=Driver()),
                ],
            ).run(job("exp-recover"), "iam")
            self.assertEqual(result.status, "completed")
            self.assertEqual(result.provider, "kaggle")
            self.assertEqual(result.recovered_from, "google_colab")

    async def test_capability_and_reflection_persisted(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            db = FakeDB()
            await ContinuousImprovement(
                db,
                store=FileSystemArtifactStore(tmp),
                adapters=[ColabResearchAdapter(driver=Driver())],
            ).run(job("exp-score"), "iam")
        self.assertTrue(any(isinstance(row, ReflectionEntry) for row in db.rows))
        self.assertTrue(any(isinstance(row, CapabilityAssessment) for row in db.rows))
        self.assertTrue(any(isinstance(row, CapabilityDefinition) for row in db.rows))


if __name__ == "__main__":
    unittest.main()
