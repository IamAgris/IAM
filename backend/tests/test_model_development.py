"""Governance tests for IAM's foundation-model development cycle.

The cognitive developer may assess and prepare candidates autonomously, but
training and release are delegated to the existing ``ai_research`` stack and
promotion goes through the signed Creator authorization gate. No boolean flag
can stand in for that authority.
"""

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.orchestration.model_development import (
    CapabilityAssessment,
    FoundationModelDeveloper,
)
from app.services.ai_research.artifacts import (
    ArtifactKind,
    FileSystemArtifactStore,
    artifact_key,
)
from app.services.ai_research.benchmarks import BenchmarkResult
from app.services.ai_research.release_gate import ModelReleaseError, ModelReleaseService


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
            }

    return Approvals


def benchmark(store, filename, mean):
    result = BenchmarkResult(
        spec_name="reasoning",
        task_type="reasoning",
        model="local-qwen-v2",
        experiment_id="exp-1",
        scores=[mean, mean],
        mean=mean,
        stdev=0.0,
        config_hash="cfg-1",
        hardware={"checkpoint_ref": "ckpt"},
    )
    key = artifact_key("exp-1", ArtifactKind.BENCHMARK, filename)
    store.put(key, json.dumps(result.to_dict(), sort_keys=True).encode("utf-8"))
    return key


class FakeAdapter:
    def credentials_available(self):
        return True


def weakness(capability, score, confidence=0.5):
    return CapabilityAssessment(
        model_id="qwen2.5:3b",
        capability=capability,
        score=score,
        confidence=confidence,
        evidence="held-out evaluation",
        dataset="held_out_eval",
        assessed_at="2026-11-27T10:00:00+00:00",
    )


class CognitiveDevelopmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_assessment_runs_one_evaluation_and_maps_all_domains(self):
        from app.orchestration.evaluation_suite import DomainResult, EvaluationReport

        report = EvaluationReport(
            run_id="run-1",
            model="qwen2.5:3b",
            overall_score=0.7,
            overall_passed=True,
            domains=[
                DomainResult("reasoning", 0.5, 10, 5, 0.7, False, "sha"),
                DomainResult("coding", 0.9, 10, 9, 0.7, True, "sha"),
            ],
            created_at="2026-11-27T10:00:00+00:00",
        )
        developer = FoundationModelDeveloper(FakeDB())
        with (
            patch(
                "app.orchestration.evaluation_suite.EvaluationSuite.run_evaluation",
                new=AsyncMock(return_value=report),
            ) as evaluate,
            patch(
                "app.services.iam_context.record_belief", new=AsyncMock()
            ) as record,
        ):
            results = await developer.assess_capabilities(
                "qwen2.5:3b", domains=["reasoning", "coding", "tool_use"]
            )

        evaluate.assert_awaited_once()
        self.assertEqual(len(results), 3)
        self.assertEqual({r.capability for r in results},
                         {"reasoning", "coding", "tool_use"})
        unmeasured = next(r for r in results if r.capability == "tool_use")
        self.assertEqual(unmeasured.confidence, 0.0)
        self.assertEqual(record.await_count, 3)

    async def test_preparation_fails_closed_when_inputs_missing(self):
        developer = FoundationModelDeveloper(FakeDB())
        result = await developer.prepare_candidate(weakness("reasoning", 0.5))
        self.assertEqual(result["status"], "blocked")
        self.assertIn("no eligible training adapter", " ".join(result["reasons"]))
        self.assertIn("no trusted evaluator", " ".join(result["reasons"]))

    async def test_preparation_delegates_to_research_pipeline(self):
        developer = FoundationModelDeveloper(
            FakeDB(),
            adapters=[FakeAdapter()],
            evaluate=lambda _spec, _model: 0.8,
            evaluator_provenance={
                "eval_manifest": "eval.jsonl",
                "eval_manifest_sha256": "abc123",
            },
            checkpoint_ref="experiments/exp-1/checkpoint/model.safetensors",
            candidate_model="local-qwen-v2",
            licence="CC-BY-4.0",
        )
        outcome = {
            "status": "candidate",
            "model": "local-qwen-v2",
            "version": "v1",
            "post_score": 0.8,
            "promoted": False,
        }
        with patch(
            "app.services.ai_research.self_improvement.prepare_candidate",
            new=AsyncMock(return_value=outcome),
        ) as prepare:
            result = await developer.prepare_candidate(weakness("reasoning", 0.5))

        prepare.assert_awaited_once()
        request = prepare.await_args.args[1]
        self.assertEqual(request.task_type, "reasoning")
        self.assertEqual(request.candidate_model, "local-qwen-v2")
        self.assertEqual(request.baseline_score, 0.5)
        self.assertEqual(request.benchmark_spec.evaluator, "custom")
        self.assertEqual(
            request.benchmark_spec.config["eval_manifest_sha256"], "abc123"
        )
        self.assertEqual(result["status"], "candidate")
        self.assertFalse(result["promoted"])

    async def test_cycle_never_prepares_for_unmeasured_domains(self):
        developer = FoundationModelDeveloper(FakeDB())
        with (
            patch.object(
                developer,
                "assess_capabilities",
                new=AsyncMock(return_value=[
                    weakness("reasoning", 0.5),
                    weakness("tool_use", 0.0, confidence=0.0),
                ]),
            ),
            patch.object(
                developer,
                "prepare_candidate",
                new=AsyncMock(return_value={"status": "blocked", "reasons": ["missing"]}),
            ) as prepare,
        ):
            summary = await developer.run_development_cycle()

        prepare.assert_awaited_once()
        self.assertEqual(prepare.await_args.args[0].capability, "reasoning")
        self.assertFalse(summary["promoted"])
        self.assertEqual(summary["candidates_prepared"], 0)
        self.assertEqual(len(summary["blocked"]), 1)


class SignedReleaseThroughDeveloperTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = FileSystemArtifactStore(Path(self.tmp.name) / "release")
        self.db = FakeDB()
        await ModelReleaseService(self.db, store=self.store).register(
            model="local-qwen-v2",
            version="v1",
            checkpoint_ref="experiments/exp-1/checkpoint/model.safetensors",
            capability_profile={"reasoning": 0.8},
            baseline_score=0.60,
            min_improvement=0.05,
            dataset_ref="datasets/clean-v3",
            dataset_sha256="a" * 64,
            licence="CC-BY-4.0",
            consent_recorded=True,
            poisoning_scan_ref="experiments/exp-1/result/poisoning.json",
            benchmark_ref="experiments/exp-1/benchmark/first.json",
            actor="iam",
        )
        self.refs = [
            benchmark(self.store, "first.json", 0.72),
            benchmark(self.store, "second.json", 0.73),
        ]
        self.developer = FoundationModelDeveloper(self.db, store=self.store)

    async def test_promotion_denied_without_signed_authorization(self):
        with (
            patch(
                "app.services.ai_research.release_gate.CreatorApprovalService",
                approvals(False),
            ),
            self.assertRaises(ModelReleaseError),
        ):
            await self.developer.promote("local-qwen-v2", "v1", self.refs)

        # No release row may be marked primary without signed authority.
        self.assertFalse(
            any(
                row.is_primary
                for row in self.db.rows
                if type(row).__name__ == "ModelVersion"
            )
        )

    async def test_signed_promote_and_rollback(self):
        from app.models.development import UpgradeHistory

        with (
            patch(
                "app.services.ai_research.release_gate.CreatorApprovalService",
                approvals(True),
            ),
            patch("app.services.ai_research.release_gate.serving_model") as serving,
        ):
            promoted = await self.developer.promote(
                "local-qwen-v2", "v1", self.refs
            )
            self.assertEqual(promoted["status"], "deployed")
            serving.activate.assert_called_once()

            rolled_back = await self.developer.rollback(
                "local-qwen-v2", "v1", "regression"
            )
            self.assertEqual(rolled_back["status"], "deployed")
            serving.rollback.assert_called_once()

        self.assertTrue(
            any(
                row.status == "rolled_back"
                for row in self.db.rows
                if isinstance(row, UpgradeHistory)
            )
        )


class ModelDevelopmentGraphTests(unittest.IsolatedAsyncioTestCase):
    def test_model_development_node_is_wired_after_honesty(self):
        from langgraph.checkpoint.memory import MemorySaver

        from app.orchestration.autonomy_graph import build_graph

        graph = build_graph(MemorySaver())
        edges = [(e.source, e.target) for e in graph.get_graph().edges]
        self.assertIn(("honesty", "model_development"), edges)
        self.assertIn(("model_development", "update_memory"), edges)

    async def test_node_supplies_research_adapters_and_evaluator(self):
        from app.orchestration import autonomy_graph

        class SessionContext:
            async def __aenter__(self):
                return FakeDB()

            async def __aexit__(self, *args):
                return False

        captured = {}

        class FakeDeveloper:
            def __init__(self, _db, **kwargs):
                captured.update(kwargs)

            async def run_development_cycle(self, _db):
                return {
                    "assessments": [],
                    "candidates_prepared": 0,
                    "candidates": [],
                    "blocked": [],
                    "details": [],
                    "promoted": False,
                }

        evaluator = SimpleNamespace(evaluate=lambda _spec, _model: 0.8)
        with (
            patch.object(autonomy_graph, "_evaluation_due", return_value=True),
            patch.object(autonomy_graph, "_session", return_value=SessionContext()),
            patch.object(autonomy_graph, "FoundationModelDeveloper", FakeDeveloper),
            patch(
                "app.services.ai_research.continuous_improvement.default_adapters",
                return_value=[object()],
            ),
            patch(
                "app.services.ai_research.lm_eval.default_eval_suite",
                return_value=evaluator,
            ),
            patch(
                "app.services.ai_research.lm_eval.eval_suite_config",
                return_value={"eval_manifest": "eval.jsonl", "eval_manifest_sha256": "abc"},
            ),
        ):
            result = await autonomy_graph.model_development({})

        self.assertTrue(captured["adapters"])
        self.assertIs(captured["evaluate"], evaluator.evaluate)
        self.assertEqual(captured["evaluator_provenance"]["eval_manifest_sha256"], "abc")
        self.assertFalse(result["model_development_summary"]["promoted"])


if __name__ == "__main__":
    unittest.main()
