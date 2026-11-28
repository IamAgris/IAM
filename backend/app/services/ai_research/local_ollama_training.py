"""Local Ollama training driver for IAM's foundation-model development.

This is an honest, local-first alternative to a free notebook platform. It
creates a real servable model tag through Ollama's ``/api/create`` endpoint
from a versioned Modelfile and writes a checkpoint artifact that the normal
benchmark and signed-release gates can consume.

It is **prompt/template adaptation, not weight fine-tuning**: no LoRA adapters
are trained here. A resulting candidate is only admissible after reproducible
benchmarks prove an improvement; the driver never promotes anything.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.services.ai_research.adapters import ResearchAdapterBase
from app.services.ai_research.artifacts import (
    ArtifactKind,
    artifact_key,
    default_store,
)
from app.services.free_sandboxes.base import (
    EnvironmentState,
    SandboxCapability,
    SandboxEnvironment,
    SandboxError,
)


def _system_prompt(weakness: str) -> str:
    return (
        "You are IAM. Maintain its identity, memory discipline and governance "
        "boundaries. Focus on improving this measured capability: " + weakness[:500]
    )


class LocalOllamaTrainingDriver:
    """ResearchDriver that materialises a candidate model in local Ollama."""

    def __init__(
        self,
        *,
        base_model: str,
        candidate_model: str,
        weakness: str = "",
        base_url: Optional[str] = None,
        client_factory: Any = None,
        store: Any = None,
        timeout: float = 300.0,
    ):
        self.base_model = base_model
        self.candidate_model = candidate_model
        self.weakness = weakness
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._client_factory = client_factory or httpx.AsyncClient
        self.store = store or default_store()
        self.timeout = timeout
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def _modelfile(self) -> str:
        return (
            f"FROM {self.base_model}\n"
            f'SYSTEM """{_system_prompt(self.weakness)}"""\n'
        )

    async def provision(self, request: Any) -> str:
        experiment_id = getattr(request, "task_id", "local") or "local"
        external_id = f"ollama-create-{uuid.uuid4().hex[:12]}"
        modelfile_ref = artifact_key(
            experiment_id, ArtifactKind.CODE, "Modelfile"
        )
        self.store.put(
            modelfile_ref,
            self._modelfile().encode("utf-8"),
            {"content_type": "text/plain", "base_model": self.base_model},
        )
        self._jobs[external_id] = {
            "experiment_id": experiment_id,
            "modelfile_ref": modelfile_ref,
            "modelfile": self._modelfile(),
        }
        return external_id

    async def start(self, external_id: str) -> None:
        job = self._jobs.get(external_id)
        if job is None:
            raise SandboxError(f"unknown local training job: {external_id}")
        async with self._client_factory(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/create",
                json={
                    "name": self.candidate_model,
                    "modelfile": job["modelfile"],
                    "stream": False,
                },
            )
        if response.status_code >= 400:
            raise SandboxError(
                f"ollama create failed: {response.status_code} {response.text[:200]}"
            )

    async def status(self, external_id: str) -> EnvironmentState:
        if external_id not in self._jobs:
            return EnvironmentState.FAILED
        try:
            async with self._client_factory(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
            names = {
                item.get("name")
                for item in (response.json().get("models") or [])
            }
        except Exception:
            return EnvironmentState.RUNNING
        return (
            EnvironmentState.COMPLETED
            if self.candidate_model in names
            else EnvironmentState.RUNNING
        )

    async def collect(self, external_id: str) -> Dict[str, Any]:
        job = self._jobs.get(external_id)
        if job is None:
            raise SandboxError(f"unknown local training job: {external_id}")
        checkpoint_ref = artifact_key(
            job["experiment_id"], ArtifactKind.CHECKPOINT, "checkpoint.json"
        )
        checkpoint = {
            "method": "ollama_create",
            "model": self.candidate_model,
            "base_model": self.base_model,
            "modelfile_ref": job["modelfile_ref"],
            "weight_fine_tuning": False,
        }
        self.store.put(
            checkpoint_ref,
            json.dumps(checkpoint, sort_keys=True).encode("utf-8"),
            {"content_type": "application/json"},
        )
        return {"checkpoint_ref": checkpoint_ref, **checkpoint}


class LocalOllamaResearchAdapter(ResearchAdapterBase):
    """Platform adapter exposing the local driver to TrainingService."""

    def __init__(self, driver: LocalOllamaTrainingDriver):
        from datetime import datetime, timezone

        from app.services.ai_research.quotas import ResearchQuotaSnapshot

        quota = ResearchQuotaSnapshot(
            provider="local_ollama",
            used_percent=0.0,
            verified_at=datetime.now(timezone.utc).isoformat(),
            source_url="local://ollama",
            reason="local runtime; no external quota",
        )
        super().__init__(
            name="local_ollama",
            capabilities={
                SandboxCapability.NOTEBOOK,
                SandboxCapability.MODEL_EVALUATION,
            },
            terms_url="local://ollama",
            quota=quota,
            notes="Local prompt/template adaptation; no weight fine-tuning.",
            driver=driver,
        )


def local_training_adapters(
    *,
    base_model: str,
    candidate_model: str,
    weakness: str = "",
    store: Any = None,
    client_factory: Any = None,
) -> list[LocalOllamaResearchAdapter]:
    """Build the local adapter set for one development cycle."""
    driver = LocalOllamaTrainingDriver(
        base_model=base_model,
        candidate_model=candidate_model,
        weakness=weakness,
        store=store,
        client_factory=client_factory,
    )
    return [LocalOllamaResearchAdapter(driver=driver)]
