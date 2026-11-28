"""Phase 3 acceptance tests for OD-41 (A8 serving, A9 training)."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.services.ai_research import (
    ColabResearchAdapter,
    FileSystemArtifactStore,
    FineTuneSpec,
    HardwareRequirement,
    NoImprovement,
    ResearchCoordinator,
    ResearchMethod,
    ServingExperimentRunner,
    ServingSpec,
    ServingUnsupported,
    TrainingService,
    validate_serving_spec,
)
from app.services.ai_research.artifacts import ArtifactKind
from app.services.ai_research.base import InvalidResearchJob
from app.services.free_sandboxes.base import EnvironmentState


class OpenAIStubHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path == "/v1/models":
            self._send({"data": [{"id": "Qwen2.5-Coder-3B"}]})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        json.loads(self.rfile.read(length))
        self._send(
            {
                "model": "Qwen2.5-Coder-3B",
                "choices": [{"message": {"role": "assistant", "content": "OK"}}],
                "usage": {"completion_tokens": 2, "prompt_tokens": 5},
            }
        )

    def _send(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def openai_stub():
    server = ThreadingHTTPServer(("127.0.0.1", 0), OpenAIStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1]
    server.shutdown()
    thread.join(timeout=5)


class StubServingDriver:
    def __init__(self, port):
        self.port = port
        self.stopped = False

    async def start(self, spec):
        from app.services.ai_research import ServingEndpoint

        return ServingEndpoint(
            base_url=f"http://127.0.0.1:{self.port}",
            model=spec.model,
            engine=spec.engine,
            provider="stub",
            external_id="srv-1",
        )

    async def health(self, endpoint):
        return True

    async def metrics(self, endpoint):
        return {"peak_vram_mb": 12000}

    async def stop(self, endpoint):
        self.stopped = True


class StubTrainingDriver:
    def __init__(self):
        self.environments = {}
        self.counter = 0

    async def provision(self, request):
        self.counter += 1
        external_id = f"train-{self.counter}"
        self.environments[external_id] = EnvironmentState.PROVISIONING
        return external_id

    async def start(self, external_id):
        self.environments[external_id] = EnvironmentState.RUNNING

    async def status(self, external_id):
        return self.environments[external_id]

    async def collect(self, external_id):
        return {"checkpoint": "s3://iam-research/checkpoints/qlora-v1"}


# ---- A8: serving -------------------------------------------------------------------
def test_a8_vllm_openai_compatible_smoke_and_report(tmp_path, openai_stub):
    store = FileSystemArtifactStore(tmp_path / "store")
    driver = StubServingDriver(openai_stub)
    runner = ServingExperimentRunner(store, driver)
    spec = ServingSpec(
        experiment_id="exp_serving",
        model="Qwen2.5-Coder-3B",
        engine="vllm",
        gpu_name="T4",
        gpu_capability=7.5,
        vram_mb=16000,
        max_tokens=32,
    )
    report = asyncio.run(runner.run(spec, prompts=["hello"]))

    assert report.healthy is True
    assert report.responses[0]["content"] == "OK"
    assert report.tokens_per_second > 0
    assert report.peak_vram_mb == 12000
    assert driver.stopped is True
    artifacts = store.list("exp_serving")
    assert artifacts[0].kind == ArtifactKind.BENCHMARK
    assert b"tokens_per_second" in store.get(artifacts[0].relative_path)


def test_a8_p100_is_refused_for_vllm_serving(tmp_path):
    spec = ServingSpec(
        experiment_id="exp_p100",
        model="Qwen2.5-Coder-3B",
        engine="vllm",
        gpu_name="P100",
        gpu_capability=6.0,
        vram_mb=16000,
    )
    with pytest.raises(ServingUnsupported):
        validate_serving_spec(spec)


def test_a8_ollama_serving_needs_no_cuda_capability():
    spec = ServingSpec(experiment_id="exp_ollama", model="Qwen2.5-Coder-3B", engine="ollama")
    validate_serving_spec(spec)  # no exception


# ---- A9: training ------------------------------------------------------------------
def test_a9_qlora_job_builds_with_dataset_and_hyperparameters(tmp_path):
    spec = FineTuneSpec(
        experiment_id="exp_train_1",
        base_model="Qwen2.5-Coder-3B",
        dataset_ref="s3://iam-datasets/code-v1",
        method=ResearchMethod.QLORA,
        epochs=2,
        quantization="4bit",
    )
    job = spec.to_job()
    assert job.dataset_ref == "s3://iam-datasets/code-v1"
    assert job.method == ResearchMethod.QLORA
    assert job.metadata["quantization"] == "4bit"
    assert job.metadata["epochs"] == 2


def test_a9_training_job_submits_and_checkpoint_is_persisted(tmp_path):
    store = FileSystemArtifactStore(tmp_path / "store")
    adapter = ColabResearchAdapter(driver=StubTrainingDriver())
    coordinator = ResearchCoordinator(store=store)
    service = TrainingService(coordinator, store)
    spec = FineTuneSpec(
        experiment_id="exp_train_2",
        base_model="Qwen2.5-Coder-3B",
        dataset_ref="s3://iam-datasets/code-v1",
        method=ResearchMethod.QLORA,
        hardware=HardwareRequirement(min_ram_mb=4096, max_runtime_minutes=60),
    )
    run, job = asyncio.run(service.submit(spec, [adapter]))

    record = service.record_checkpoint(run, "s3://iam-research/checkpoints/qlora-v1")
    assert record["checkpoint_ref"].startswith("s3://")
    artifacts = store.list("exp_train_2")
    assert any(a.kind == ArtifactKind.CHECKPOINT for a in artifacts)
    assert any(a.kind == ArtifactKind.JOB_SPEC for a in artifacts)


def test_a9_quality_gate_rejects_no_improvement():
    TrainingService.validate_improvement(0.70, 0.80)
    with pytest.raises(NoImprovement):
        TrainingService.validate_improvement(0.70, 0.65)


def test_a9_training_spec_validation_fail_closed():
    spec = FineTuneSpec(
        experiment_id="exp_bad",
        base_model="model",
        dataset_ref="",
        method=ResearchMethod.QLORA,
    )
    with pytest.raises(InvalidResearchJob):
        spec.to_job()
