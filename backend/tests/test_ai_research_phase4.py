"""Phase 4 acceptance tests for OD-41 (A10 recovery, A11 scheduling, A12 lifecycle)."""

import asyncio

import pytest

from app.services.ai_research import (
    ColabResearchAdapter,
    FileSystemArtifactStore,
    JobRecovery,
    KaggleResearchAdapter,
    PlatformLifecycle,
    ResearchCoordinator,
    ResearchJob,
    ResearchMethod,
    ResearchQuotaSnapshot,
    ResearchScheduler,
    WorkloadProfile,
)
from app.services.free_sandboxes.base import (
    EnvironmentState,
    ProviderUnavailable,
    SandboxError,
)


class FailingDriver:
    async def provision(self, request):
        raise SandboxError("colab session quota revoked")

    async def start(self, external_id):
        raise AssertionError("should never start")

    async def status(self, external_id):
        return EnvironmentState.FAILED

    async def collect(self, external_id):
        return {}


class WorkingDriver:
    def __init__(self):
        self.environments = {}

    async def provision(self, request):
        self.environments["work-1"] = EnvironmentState.PROVISIONING
        return "work-1"

    async def start(self, external_id):
        self.environments[external_id] = EnvironmentState.RUNNING

    async def status(self, external_id):
        return self.environments[external_id]

    async def collect(self, external_id):
        return {"ok": True}


def sample_job():
    return ResearchJob(
        experiment_id="exp_phase4",
        title="benchmark",
        task_type="coding",
        complexity=3,
        method=ResearchMethod.EVALUATION,
        model="Qwen2.5-Coder-3B",
        dataset_ref="s3://iam-datasets/bench-v1",
    )


# ---- A10: autonomous recovery ------------------------------------------------------
def test_a10_recovery_switches_platform_and_resumes_checkpoint(tmp_path):
    events = []
    store = FileSystemArtifactStore(tmp_path / "store")
    coordinator = ResearchCoordinator(store=store, audit_sink=lambda e, d: events.append(e))
    recovery = JobRecovery(coordinator, audit_sink=lambda e, d: events.append(e))
    failing = ColabResearchAdapter(driver=FailingDriver())
    working = KaggleResearchAdapter(driver=WorkingDriver())

    run = asyncio.run(
        recovery.recover(
            sample_job(),
            "google_colab",
            [failing, working],
            checkpoint_ref="s3://iam-research/checkpoints/step-100",
        )
    )

    assert run.provider == "kaggle"
    assert "experiment_recovered" in events
    manifest = store.get(run.artifacts[0].relative_path)
    assert b"resume_from_checkpoint" in manifest


def test_a10_recovery_exhausts_options_without_paid_fallback(tmp_path):
    store = FileSystemArtifactStore(tmp_path / "store")
    coordinator = ResearchCoordinator(store=store)
    recovery = JobRecovery(coordinator)
    failing = ColabResearchAdapter(driver=FailingDriver())
    with pytest.raises(ProviderUnavailable):
        asyncio.run(recovery.recover(sample_job(), "google_colab", [failing]))


# ---- A11: workload-aware scheduling -----------------------------------------------
def test_a11_scheduler_rejects_p100_for_cuda_serving_workload():
    colab = ColabResearchAdapter(driver=WorkingDriver())
    kaggle = KaggleResearchAdapter(driver=WorkingDriver())
    scheduler = ResearchScheduler()
    snapshots = [
        asyncio.run(colab.verify_research_quota()),
        asyncio.run(kaggle.verify_research_quota()),
    ]
    profile = WorkloadProfile(
        vram_mb=16000,
        ram_mb=7800,
        gpu_capability=7.5,
        runtime_minutes=60,
    )
    ranked = scheduler.rank([kaggle, colab], snapshots, profile)

    assert ranked[0].provider == "google_colab"
    kaggle_decision = next(d for d in ranked if d.provider == "kaggle")
    assert kaggle_decision.score < 0
    assert "ineligible" in kaggle_decision.reason


def test_a11_best_returns_none_when_no_eligible_platform():
    colab = ColabResearchAdapter(driver=WorkingDriver())
    snapshot = asyncio.run(colab.verify_research_quota())
    best = ResearchScheduler().best(
        [colab],
        [snapshot],
        WorkloadProfile(vram_mb=64000, ram_mb=7800, gpu_capability=7.5),
    )
    assert best is None


# ---- A12: platform lifecycle -------------------------------------------------------
def test_a12_degraded_platform_is_not_submitted_until_revalidated(tmp_path):
    store = FileSystemArtifactStore(tmp_path / "store")
    adapter = ColabResearchAdapter(driver=WorkingDriver())
    original = asyncio.run(adapter.verify_research_quota())
    lifecycle = PlatformLifecycle()

    assert asyncio.run(lifecycle.monitor([adapter]))["google_colab"] == "active"

    degraded = ResearchQuotaSnapshot(
        provider="google_colab",
        used_percent=95.0,
        verified_at=original.verified_at,
        source_url=original.source_url,
        gpu_name="T4",
        gpu_capability=7.5,
        vram_mb=16000,
        ram_mb=7800,
        session_limit_minutes=720,
        concurrent_jobs_limit=1,
    )
    adapter.set_quota(degraded)
    assert asyncio.run(lifecycle.monitor([adapter]))["google_colab"] == "degraded"

    coordinator = ResearchCoordinator(store=store)
    with pytest.raises(ProviderUnavailable):
        asyncio.run(
            coordinator.submit(
                sample_job(), [adapter], eligible_providers=set(lifecycle.eligible())
            )
        )

    adapter.set_quota(original)  # provider quota refreshed after degradation
    lifecycle.revalidate("google_colab", original)
    assert "google_colab" in lifecycle.eligible()
    run = asyncio.run(
        coordinator.submit(
            sample_job(), [adapter], eligible_providers=set(lifecycle.eligible())
        )
    )
    assert run.provider == "google_colab"


def test_a12_repeated_degradation_retires_provider():
    adapter = ColabResearchAdapter(driver=WorkingDriver())
    original = asyncio.run(adapter.verify_research_quota())
    degraded = ResearchQuotaSnapshot(
        provider="google_colab", used_percent=95.0,
        verified_at=original.verified_at, source_url=original.source_url,
    )
    adapter.set_quota(degraded)
    lifecycle = PlatformLifecycle(retire_after=2)
    asyncio.run(lifecycle.monitor([adapter]))
    states = asyncio.run(lifecycle.monitor([adapter]))
    assert states["google_colab"] == "retired"
    assert lifecycle.eligible() == []
