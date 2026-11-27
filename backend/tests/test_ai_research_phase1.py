"""Phase 1 acceptance tests for OD-41 (A4, A5 plus adapter/quota boundaries)."""

import asyncio
import io
from datetime import datetime, timezone

import pytest

from app.services.ai_research import (
    ColabResearchAdapter,
    FileSystemArtifactStore,
    HardwareRequirement,
    KaggleResearchAdapter,
    ResearchCoordinator,
    ResearchJob,
    ResearchMethod,
    S3ArtifactStore,
)
from app.services.free_sandboxes.base import EnvironmentState, ProviderUnavailable


class StubDriver:
    def __init__(self, results=None):
        self.environments = {}
        self.results = results or {"accuracy": 0.8}
        self.counter = 0

    async def provision(self, request):
        self.counter += 1
        external_id = f"stub-{self.counter}"
        self.environments[external_id] = {
            "state": EnvironmentState.PROVISIONING,
            "request": request,
        }
        return external_id

    async def start(self, external_id):
        self.environments[external_id]["state"] = EnvironmentState.RUNNING

    async def status(self, external_id):
        return self.environments[external_id]["state"]

    async def collect(self, external_id):
        return dict(self.results)


class StubS3Client:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, Metadata):
        self.objects[Key] = (Body, Metadata, datetime.now(timezone.utc))

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key][0])}

    def head_object(self, Bucket, Key):
        if Key not in self.objects:
            raise KeyError(Key)
        return {}

    def list_objects_v2(self, Bucket, Prefix):
        return {
            "Contents": [
                {
                    "Key": key,
                    "Metadata": value[1],
                    "LastModified": value[2],
                    "Size": len(value[0]),
                }
                for key, value in self.objects.items()
                if key.startswith(Prefix)
            ]
        }


def sample_job(**overrides):
    defaults = dict(
        experiment_id="exp_phase1_test",
        title="vLLM serving benchmark",
        task_type="coding",
        complexity=3,
        method=ResearchMethod.EVALUATION,
        model="Qwen2.5-Coder-3B",
        dataset_ref="s3://iam-datasets/bench-v1",
        hardware=HardwareRequirement(min_ram_mb=4096, max_runtime_minutes=60),
        outputs=["benchmark_report"],
    )
    defaults.update(overrides)
    return ResearchJob(**defaults)


# ---- WP6 / A5: S3-compatible store -------------------------------------------------
def test_s3_store_round_trip_and_integrity_metadata():
    client = StubS3Client()
    store = S3ArtifactStore(bucket="iam-research", client=client, prefix="core")
    artifact = store.put(
        "experiments/exp_s3/job_spec/job.json", b'{"title":"test"}', {"note": "v1"}
    )
    assert store.exists("experiments/exp_s3/job_spec/job.json")
    assert store.get("experiments/exp_s3/job_spec/job.json") == b'{"title":"test"}'
    assert artifact.sha256 == client.objects["core/experiments/exp_s3/job_spec/job.json"][1]["sha256"]
    listed = store.list("exp_s3")
    assert len(listed) == 1 and listed[0].kind.value == "job_spec"


# ---- WP4 / A4: coordinator ----------------------------------------------------------
def test_a4_coordinator_plans_submits_and_audits(tmp_path):
    events = []
    store = FileSystemArtifactStore(tmp_path / "store")
    driver = StubDriver()
    adapter = ColabResearchAdapter(driver=driver)
    coordinator = ResearchCoordinator(store=store, audit_sink=lambda e, d: events.append((e, d)))

    run = asyncio.run(coordinator.submit(sample_job(), [adapter]))

    assert run.provider == "google_colab"
    assert run.environment.external_id == "stub-1"
    assert [e for e, _ in events] == ["experiment_planned", "experiment_submitted"]
    assert events[-1][1]["experiment_id"] == "exp_phase1_test"
    assert len(run.artifacts) == 1
    assert store.exists(run.artifacts[0].relative_path)


def test_a4_request_metadata_contains_no_secret_values(tmp_path):
    from app.services.ai_research import CredentialVault

    vault = CredentialVault({"COLAB_TOKEN": "phase1secretvalue"})
    adapter = ColabResearchAdapter(driver=StubDriver())
    coordinator = ResearchCoordinator(
        store=FileSystemArtifactStore(tmp_path / "store"), vault=vault
    )
    run = asyncio.run(
        coordinator.submit(
            sample_job(),
            [adapter],
            credentials=[],
        )
    )
    assert "phase1secretvalue" not in str(run.request.metadata)


# ---- WP6 / A5: persistence after session expiry ------------------------------------
def test_a5_artifacts_survive_session_expiry(tmp_path):
    store = FileSystemArtifactStore(tmp_path / "store")
    adapter = ColabResearchAdapter(driver=StubDriver())
    coordinator = ResearchCoordinator(store=store)
    run = asyncio.run(coordinator.submit(sample_job(), [adapter]))

    adapter.expire_sessions()
    assert run.environment.state == EnvironmentState.STOPPED
    assert store.exists(run.artifacts[0].relative_path)
    assert store.get(run.artifacts[0].relative_path)


# ---- Result collection -------------------------------------------------------------
def test_collect_stores_untrusted_result(tmp_path):
    events = []
    store = FileSystemArtifactStore(tmp_path / "store")
    adapter = ColabResearchAdapter(driver=StubDriver({"note": "ghp_" + "b" * 24}))
    coordinator = ResearchCoordinator(store=store, audit_sink=lambda e, d: events.append(e))
    run = asyncio.run(coordinator.submit(sample_job(), [adapter]))
    wrapped = asyncio.run(coordinator.collect(run, adapter))

    assert wrapped["trusted"] is False
    assert wrapped["content"]["note"] == "[REDACTED]"
    assert any(a.kind.value == "result" for a in store.list("exp_phase1_test"))
    assert events[-1] == "experiment_results_collected"


# ---- WP5 adapter boundaries --------------------------------------------------------
def test_kaggle_refuses_vllm_serving_but_accepts_training():
    kaggle = KaggleResearchAdapter(driver=StubDriver())
    assert kaggle.supports(sample_job(method=ResearchMethod.QLORA)) is True
    serving = sample_job(
        method=ResearchMethod.SERVING,
        dataset_ref="",
        hardware=HardwareRequirement(min_ram_mb=4096, min_gpu_capability=7.5),
    )
    assert kaggle.supports(serving) is False


def test_adapter_without_driver_fails_closed(tmp_path):
    adapter = ColabResearchAdapter()
    coordinator = ResearchCoordinator(store=FileSystemArtifactStore(tmp_path / "store"))
    with pytest.raises(ProviderUnavailable):
        asyncio.run(coordinator.submit(sample_job(), [adapter]))


def test_paid_platform_is_never_selected(tmp_path):
    driver = StubDriver()
    adapter = ColabResearchAdapter(driver=driver)
    quota = adapter._quota
    quota.paid_required = True
    adapter.set_quota(quota)
    coordinator = ResearchCoordinator(store=FileSystemArtifactStore(tmp_path / "store"))
    with pytest.raises(ProviderUnavailable):
        asyncio.run(coordinator.submit(sample_job(), [adapter]))
    assert driver.counter == 0
