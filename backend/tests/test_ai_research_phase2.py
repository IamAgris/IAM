"""Phase 2 acceptance tests for OD-41 (A6, A7)."""

import pytest

from app.services.ai_research import (
    BenchmarkResult,
    BenchmarkRunner,
    BenchmarkSpec,
    BenchmarkUnstable,
    CapabilityRegistry,
    FileSystemArtifactStore,
    NoCapableModel,
    UnknownModel,
)
from app.services.ai_research.artifacts import ArtifactKind
from app.services.ai_research.base import ResearchError


def spec(name="normalise_path", repetitions=5):
    return BenchmarkSpec(
        name=name,
        task_type="coding",
        metric="pass_rate",
        repetitions=repetitions,
        tolerance_pct=5.0,
    )


# ---- A6: reproducibility -----------------------------------------------------------
def test_a6_repeated_benchmark_is_reproducible_and_persisted(tmp_path):
    store = FileSystemArtifactStore(tmp_path / "store")
    runner = BenchmarkRunner(store)

    first = runner.run(spec(), "tiny-model", "exp_a", {"cpu": 4}, lambda *_: 0.72)
    second = runner.run(spec(), "tiny-model", "exp_b", {"cpu": 4}, lambda *_: 0.73)

    runner.assert_reproducible(first, second)
    assert first.config_hash == second.config_hash
    assert first.scores == [0.72] * 5
    assert store.list("exp_a")[0].kind == ArtifactKind.BENCHMARK
    assert b'"mean"' in store.get(first_scores_key(store, "exp_a"))


def first_scores_key(store, experiment_id):
    return store.list(experiment_id)[0].relative_path


def test_a6_unstable_scores_are_rejected(tmp_path):
    runner = BenchmarkRunner(FileSystemArtifactStore(tmp_path / "store"))
    unstable = BenchmarkResult(
        spec_name="normalise_path",
        task_type="coding",
        model="tiny-model",
        experiment_id="exp_b",
        scores=[0.1] * 5,
        mean=0.1,
        stdev=0.0,
        config_hash="same",
        hardware={"cpu": 4},
    )
    stable = BenchmarkResult(
        spec_name="normalise_path",
        task_type="coding",
        model="tiny-model",
        experiment_id="exp_a",
        scores=[0.9] * 5,
        mean=0.9,
        stdev=0.0,
        config_hash="same",
        hardware={"cpu": 4},
    )
    with pytest.raises(BenchmarkUnstable):
        runner.assert_reproducible(stable, unstable)

    unstable.config_hash = "different"
    with pytest.raises(BenchmarkUnstable):
        runner.assert_reproducible(stable, unstable)


def test_a6_failed_experiments_are_retained(tmp_path):
    store = FileSystemArtifactStore(tmp_path / "store")
    runner = BenchmarkRunner(store)
    with pytest.raises(ResearchError):
        runner.run(spec(repetitions=1), "tiny-model", "exp_failed", {}, lambda *_: 1.8)
    artifacts = store.list("exp_failed")
    assert len(artifacts) == 1
    assert artifacts[0].relative_path.endswith("normalise_path.failed.json")
    assert b"failed" in store.get(artifacts[0].relative_path)


# ---- A7: capability profiles -------------------------------------------------------
def test_a7_profile_is_built_from_measured_results_and_used_for_selection(tmp_path):
    store = FileSystemArtifactStore(tmp_path / "store")
    runner = BenchmarkRunner(store)
    registry = CapabilityRegistry(store)

    strong = runner.run(spec(), "small-model", "exp_1", {}, lambda *_: 0.82)
    weak = runner.run(spec(), "huge-model-name", "exp_2", {}, lambda *_: 0.55)
    registry.record(strong)
    registry.record(weak)

    profile = registry.profile("small-model")
    assert profile.task_scores["coding"] == pytest.approx(0.82)
    assert registry.select(["small-model", "huge-model-name"], "coding", 0.5) == "small-model"
    assert store.list("exp_1")


def test_a7_unknown_model_and_unmet_threshold_are_refused():
    registry = CapabilityRegistry()
    with pytest.raises(UnknownModel):
        registry.profile("never-benchmarked")
    with pytest.raises(NoCapableModel):
        registry.select(["never-benchmarked"], "coding", 0.9)


def test_a7_low_scores_become_known_failures():
    registry = CapabilityRegistry()
    result = BenchmarkResult(
        spec_name="normalise_path",
        task_type="coding",
        model="weak-model",
        experiment_id="exp_weak",
        scores=[0.2],
        mean=0.2,
        stdev=0.0,
        config_hash="hash",
        hardware={},
    )
    profile = registry.record(result)
    assert profile.known_failures == ["normalise_path: mean 0.2"]
