"""WP9 — vLLM / Ollama serving experiments (OD-41).

vLLM is an alternative serving engine, not a replacement for the model. A vLLM
job is refused unless the platform advertises NVIDIA compute capability >= 7.5;
Kaggle's P100 (6.0) is therefore training-only. Live serving still requires a
platform driver with a real GPU.
"""

from __future__ import annotations

import json
import statistics
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol

from .artifacts import ArtifactKind, ArtifactStore, artifact_key
from .base import InvalidResearchJob, ResearchError


class ServingUnsupported(ResearchError):
    """The platform cannot serve this model with the requested engine."""


@dataclass
class ServingSpec:
    experiment_id: str
    model: str
    engine: str = "vllm"  # vllm | ollama
    gpu_name: str = ""
    gpu_capability: float = 0.0
    vram_mb: int = 0
    context_tokens: int = 4096
    max_tokens: int = 256
    tensor_parallel: int = 1
    port: int = 8000


def validate_serving_spec(spec: ServingSpec) -> None:
    if spec.engine not in ("vllm", "ollama"):
        raise InvalidResearchJob(f"unknown serving engine: {spec.engine}")
    if spec.engine == "vllm" and spec.gpu_capability < 7.5:
        raise ServingUnsupported(
            f"vLLM requires NVIDIA compute capability >= 7.5 "
            f"(platform reports {spec.gpu_capability} on {spec.gpu_name})"
        )
    if spec.max_tokens <= 0 or spec.context_tokens <= 0:
        raise InvalidResearchJob("token limits must be positive")
    if spec.tensor_parallel < 1:
        raise InvalidResearchJob("tensor_parallel must be >= 1")


@dataclass
class ServingEndpoint:
    base_url: str
    model: str
    engine: str
    provider: str
    external_id: str


class ServingDriver(Protocol):
    async def start(self, spec: ServingSpec) -> ServingEndpoint: ...

    async def health(self, endpoint: ServingEndpoint) -> bool: ...

    async def metrics(self, endpoint: ServingEndpoint) -> Dict[str, Any]: ...

    async def stop(self, endpoint: ServingEndpoint) -> None: ...


class OpenAICompatibleClient:
    """Minimal client for the OpenAI-compatible API exposed by vLLM/Ollama."""

    def __init__(self, endpoint: ServingEndpoint, timeout: float = 120.0) -> None:
        self.endpoint = endpoint
        self.timeout = timeout

    def health(self) -> bool:
        try:
            with urllib.request.urlopen(
                f"{self.endpoint.base_url}/v1/models", timeout=10
            ) as response:
                return response.status == 200
        except Exception:
            return False

    def chat(self, messages: List[Dict[str, str]], max_tokens: Optional[int] = None) -> dict:
        payload = json.dumps(
            {
                "model": self.endpoint.model,
                "messages": messages,
                "max_tokens": max_tokens or 64,
                "temperature": 0,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.endpoint.base_url}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        latency_ms = (time.perf_counter() - started) * 1000
        choice = body["choices"][0]
        return {
            "content": choice["message"]["content"],
            "usage": body.get("usage", {}),
            "latency_ms": round(latency_ms, 2),
            "model": body.get("model"),
        }


@dataclass
class ServingReport:
    experiment_id: str
    provider: str
    engine: str
    model: str
    healthy: bool
    responses: List[dict]
    median_latency_ms: float
    tokens_per_second: float
    peak_vram_mb: int
    concurrency: int
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ServingExperimentRunner:
    def __init__(
        self,
        store: ArtifactStore,
        driver: ServingDriver,
        client_factory=OpenAICompatibleClient,
    ) -> None:
        self.store = store
        self.driver = driver
        self.client_factory = client_factory

    async def run(
        self,
        spec: ServingSpec,
        prompts: Optional[List[str]] = None,
        concurrency: int = 1,
    ) -> ServingReport:
        validate_serving_spec(spec)
        prompts = prompts or ["Reply with exactly OK and nothing else."]
        endpoint = await self.driver.start(spec)
        try:
            client = self.client_factory(endpoint)
            healthy = bool(await self.driver.health(endpoint)) and client.health()
            responses = [
                client.chat([{"role": "user", "content": prompt}], spec.max_tokens)
                for prompt in prompts
            ]
            metrics = await self.driver.metrics(endpoint)
            latencies = [r["latency_ms"] for r in responses]
            completion_tokens = sum(r["usage"].get("completion_tokens", 0) for r in responses)
            elapsed = sum(latencies) / 1000 or 1.0
            report = ServingReport(
                experiment_id=spec.experiment_id,
                provider=endpoint.provider,
                engine=spec.engine,
                model=spec.model,
                healthy=healthy,
                responses=responses,
                median_latency_ms=round(statistics.median(latencies), 2),
                tokens_per_second=round(completion_tokens / elapsed, 2),
                peak_vram_mb=int(metrics.get("peak_vram_mb", spec.vram_mb)),
                concurrency=concurrency,
            )
            if not healthy or not all(r["content"] for r in responses):
                raise ResearchError("serving endpoint failed its OpenAI-compatible smoke test")
        finally:
            await self.driver.stop(endpoint)

        self.store.put(
            artifact_key(spec.experiment_id, ArtifactKind.BENCHMARK, "serving_report.json"),
            json.dumps(report.to_dict(), sort_keys=True, indent=2).encode("utf-8"),
        )
        return report
