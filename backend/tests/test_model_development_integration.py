"""Integration evidence for the unattended model-development chain.

Exercises the real ``self_improvement.prepare_candidate`` stages — training
submission, two reproducible benchmarks, candidate registration — plus the real
signed release and rollback gates. Only two external boundaries are replaced:
the Creator approval service (an authority, never IAM's own) and the consented
dataset build (no owner consent is configured in this environment).

This proves orchestration integrity, not a measured capability gain: no GPU
training runs here.
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.orchestration.model_development import CapabilityAssessment, FoundationModelDeveloper
from app.services.ai_research.adapters import ColabResearchAdapter
from app.services.ai_research.artifacts import FileSystemArtifactStore
from app.services.free_sandboxes.base import EnvironmentState, SandboxCapability, SandboxEnvironment


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
                import uuid

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


class LocalDriver:
    """Deterministic stand-in for a free platform driver (no GPU work)."""

    async def provision(self, request):
        return "local-test-run"

    async def start(self, external_id):
        return None

    async def status(self, external_id):
        return SandboxEnvironment(
            provider="google_colab",
            external_id=external_id,
            capability=SandboxCapability.NOTEBOOK,
            state=EnvironmentState.COMPLETED,
        )

    async def collect(self, external_id):
        return {"checkpoint_ref": "experiments/local/checkpoint/model.safetensors"}


def dataset_result():
    return SimpleNamespace(
        dataset_ref="experiments/local/dataset/dataset.jsonl",
        dataset_sha256="a" * 64,
        poisoning_scan_ref="experiments/local/result/poisoning.json",
        manifest_ref="experiments/local/job_spec/job.json",
        licence="CC-BY-4.0",
        consent_recorded=True,
        personal_data_included=False,
        row_count=4,
        as_dict=lambda: {"row_count": 4, "licence": "CC-BY-4.0"},
    )


def approvals():
    class Approvals:
        def __init__(self, _db):
            pass

        async def check_authorization(self, _action, target_ref=None):
            return {
                "authorized": True,
                "authorization_id": "signed-auth-1",
                "signer_id": "creator-signer",
                "target_ref": target_ref,
            }

    return Approvals


class DevelopmentChainIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = FileSystemArtifactStore(Path(self.tmp.name) / "chain")
        self.db = FakeDB()
        self.developer = FoundationModelDeveloper(
            self.db,
            adapters=[ColabResearchAdapter(driver=LocalDriver())],
            evaluate=lambda _spec, _model: 0.8,
            evaluator_provenance={
                "eval_manifest": "eval.jsonl",
                "eval_manifest_sha256": "b" * 64,
            },
            store=self.store,
            checkpoint_ref="experiments/local/checkpoint/model.safetensors",
            candidate_model="local-qwen-v2",
            licence="CC-BY-4.0",
        )
        self.weakness = CapabilityAssessment(
            model_id="qwen2.5:3b",
            capability="reasoning",
            score=0.5,
            confidence=0.5,
            evidence="held-out evaluation",
            dataset="held_out_eval",
            assessed_at="2026-11-27T10:00:00+00:00",
        )

    async def test_prepare_register_promote_and_rollback(self):
        with (
            patch(
                "app.services.ai_research.self_improvement.build_dataset",
                new=AsyncMock(return_value=dataset_result()),
            ),
            patch(
                "app.services.ai_research.release_gate.CreatorApprovalService",
                approvals(),
            ),
            patch("app.services.ai_research.release_gate.serving_model"),
        ):
            candidate = await self.developer.prepare_candidate(self.weakness)
            self.assertEqual(candidate["status"], "candidate")
            self.assertEqual(candidate["post_score"], 0.8)
            self.assertEqual(len(candidate["benchmark_refs"]), 2)
            self.assertFalse(candidate["promoted"])

            promoted = await self.developer.promote(
                candidate["model"], candidate["version"], candidate["benchmark_refs"]
            )
            self.assertEqual(promoted["status"], "deployed")

            rolled_back = await self.developer.rollback(
                candidate["model"], candidate["version"], "regression"
            )
            self.assertEqual(rolled_back["status"], "deployed")


if __name__ == "__main__":
    unittest.main()
