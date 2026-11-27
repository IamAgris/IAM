"""Orchestrator links the existing stages and never auto-promotes."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.ai_research import self_improvement
from app.services.ai_research.artifacts import FileSystemArtifactStore
from app.services.ai_research.base import InvalidResearchJob
from app.services.ai_research.benchmarks import BenchmarkResult


def dataset_result(licence="CC-BY-4.0"):
    return SimpleNamespace(
        dataset_ref="experiments/exp/dataset/dataset.jsonl",
        dataset_sha256="abc",
        poisoning_scan_ref="experiments/exp/result/poisoning.json",
        manifest_ref="experiments/exp/job_spec/job.json",
        licence=licence,
        consent_recorded=bool(licence),
        personal_data_included=False,
        row_count=1,
        as_dict=lambda: {"row_count": 1},
    )


def benchmark(mean, model="local-qwen-coder-3b-v2"):
    return BenchmarkResult(
        spec_name="coding-regression",
        task_type="coding",
        model=model,
        experiment_id="exp_test",
        scores=[mean, mean],
        mean=mean,
        stdev=0.0,
        config_hash="same-config",
        hardware={"checkpoint_ref": "ckpt"},
    )


class FakeDB:
    pass


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = FileSystemArtifactStore(Path(self.tmp.name) / "store")
        self.request = self_improvement.CandidateRequest(
            experiment_id="exp_test",
            licence="CC-BY-4.0",
            base_model="local-qwen-coder-3b",
            candidate_model="local-qwen-coder-3b-v2",
            checkpoint_ref="ckpt",
            baseline_score=0.5,
            min_improvement=0.01,
            diagnosis="weak at tool use",
        )

    async def _run(self, **overrides):
        patches = (
            patch.object(
                self_improvement,
                "build_dataset",
                new=AsyncMock(return_value=dataset_result(**overrides)),
            ),
            patch.object(
                self_improvement.TrainingService,
                "submit",
                new=AsyncMock(
                    return_value=(
                        SimpleNamespace(job=SimpleNamespace(experiment_id="exp_test")),
                        SimpleNamespace(experiment_id="exp_test"),
                    )
                ),
            ),
            patch.object(
                self_improvement.BenchmarkRunner,
                "run",
                side_effect=[benchmark(0.8), benchmark(0.8)],
            ),
            patch.object(
                self_improvement.CapabilityRegistry,
                "record",
                return_value=SimpleNamespace(to_dict=lambda: {"coding": 0.8}),
            ),
            patch.object(
                self_improvement.ModelReleaseService,
                "register",
                new=AsyncMock(return_value={"status": "candidate"}),
            ),
            patch.object(self_improvement, "serving_model", create=True),
        )
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        return await self_improvement.prepare_candidate(
            FakeDB(),
            self.request,
            store=self.store,
            adapters=[object()],
            evaluate=lambda _spec, _model: 0.8,
        )

    async def test_candidate_is_registered_but_not_promoted(self):
        result = await self._run()
        self.assertEqual(result["status"], "candidate")
        self.assertEqual(result["promoted"], False)
        self.assertEqual(result["model"], "local-qwen-coder-3b-v2")
        self.assertEqual(result["base_model"], "local-qwen-coder-3b")
        self.assertEqual(result["post_score"], 0.8)
        self.assertEqual(len(result["benchmark_refs"]), 2)
        self.assertNotEqual(result["benchmark_refs"][0], result["benchmark_refs"][1])

    async def test_missing_evaluator_fails_closed(self):
        with (
            patch.object(
                self_improvement, "default_lm_eval_driver", return_value=None
            ),
            patch.object(self_improvement, "default_eval_suite", return_value=None),
            self.assertRaises(InvalidResearchJob),
        ):
            await self_improvement.prepare_candidate(
                FakeDB(), self.request, store=self.store, adapters=[object()]
            )

    async def test_no_adapter_fails_closed(self):
        with self.assertRaises(InvalidResearchJob):
            await self_improvement.prepare_candidate(
                FakeDB(),
                self.request,
                store=self.store,
                adapters=[],
                evaluate=lambda _spec, _model: 0.8,
            )

    async def test_benchmark_measures_candidate_not_base_model(self):
        with (
            patch.object(
                self_improvement,
                "build_dataset",
                new=AsyncMock(return_value=dataset_result()),
            ),
            patch.object(
                self_improvement.TrainingService,
                "submit",
                new=AsyncMock(
                    return_value=(
                        SimpleNamespace(job=SimpleNamespace(experiment_id="exp_test")),
                        SimpleNamespace(experiment_id="exp_test"),
                    )
                ),
            ),
            patch.object(
                self_improvement.BenchmarkRunner,
                "run",
                side_effect=[benchmark(0.8), benchmark(0.8)],
            ) as run,
            patch.object(
                self_improvement.CapabilityRegistry,
                "record",
                return_value=SimpleNamespace(to_dict=lambda: {"coding": 0.8}),
            ),
            patch.object(
                self_improvement.ModelReleaseService,
                "register",
                new=AsyncMock(return_value={"status": "candidate"}),
            ),
        ):
            await self_improvement.prepare_candidate(
                FakeDB(),
                self.request,
                store=self.store,
                adapters=[object()],
                evaluate=lambda _spec, _model: 0.8,
            )
        measured = [call.args[1] for call in run.call_args_list]
        self.assertEqual(measured, ["local-qwen-coder-3b-v2", "local-qwen-coder-3b-v2"])

    async def test_unserved_candidate_fails_closed(self):
        request = self_improvement.CandidateRequest(
            experiment_id="exp_test",
            licence="CC-BY-4.0",
            base_model="local-qwen-coder-3b",
            checkpoint_ref="ckpt",
            baseline_score=0.5,
        )
        with self.assertRaises(InvalidResearchJob):
            await self_improvement.prepare_candidate(
                FakeDB(), request, store=self.store, adapters=[object()]
            )

    async def test_incomplete_provenance_fails_before_submission(self):
        with patch.object(
            self_improvement,
            "build_dataset",
            new=AsyncMock(return_value=dataset_result(licence="")),
        ):
            with self.assertRaises(InvalidResearchJob):
                await self_improvement.prepare_candidate(
                    FakeDB(),
                    self.request,
                    store=self.store,
                    adapters=[object()],
                    evaluate=lambda _spec, _model: 0.8,
                )


if __name__ == "__main__":
    unittest.main()
