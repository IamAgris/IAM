"""WP4 — research coordinator: plan, submit and collect experiments (OD-41).

The coordinator does not own credentials or protected data. It picks an
eligible free platform using the GPU-aware quota gate, persists the job spec
before submission, and stores returned results as untrusted data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Set

from ..free_sandboxes.base import ProviderUnavailable, SandboxCapability, SandboxEnvironment, WorkloadRequest
from .adapters import ResearchPlatformAdapter
from .artifacts import ArtifactKind, ArtifactStore, ResearchArtifact, artifact_key
from .credentials import CredentialRef, CredentialVault
from .jobs import ResearchJob, ResearchMethod
from .quotas import ResearchQuotaGuard
from .security import wrap_research_output
from .service import prepare_job

AuditSink = Callable[[str, Dict[str, Any]], None]

METHOD_CAPABILITY: Dict[ResearchMethod, SandboxCapability] = {
    ResearchMethod.SFT: SandboxCapability.DEVELOPMENT,
    ResearchMethod.LORA: SandboxCapability.DEVELOPMENT,
    ResearchMethod.QLORA: SandboxCapability.DEVELOPMENT,
    ResearchMethod.FULL_FINE_TUNE: SandboxCapability.DEVELOPMENT,
    ResearchMethod.DISTILLATION: SandboxCapability.DEVELOPMENT,
    ResearchMethod.EVALUATION: SandboxCapability.MODEL_EVALUATION,
    ResearchMethod.SERVING: SandboxCapability.INFERENCE,
}


@dataclass
class ResearchRun:
    job: ResearchJob
    provider: str
    environment: SandboxEnvironment
    request: WorkloadRequest
    artifacts: List[ResearchArtifact] = field(default_factory=list)
    results: Optional[dict] = None  # type: ignore[type-arg]


class ResearchCoordinator:
    def __init__(
        self,
        store: ArtifactStore,
        guard: Optional[ResearchQuotaGuard] = None,
        vault: Optional[CredentialVault] = None,
        audit_sink: Optional[AuditSink] = None,
    ) -> None:
        self.store = store
        self.guard = guard or ResearchQuotaGuard()
        self.vault = vault
        self.audit_sink = audit_sink

    def _audit(self, event: str, details: Dict[str, Any]) -> None:
        if self.audit_sink:
            self.audit_sink(event, details)

    async def submit(
        self,
        job: ResearchJob,
        adapters: Iterable[ResearchPlatformAdapter],
        credentials: Iterable[CredentialRef] = (),
        private_markers: Iterable[str] = (),
        eligible_providers: Optional[Set[str]] = None,
    ) -> ResearchRun:
        prepared = prepare_job(
            job,
            self.store,
            vault=self.vault,
            credentials=credentials,
            private_markers=private_markers,
        )
        self._audit("experiment_planned", {
            "experiment_id": job.experiment_id,
            "method": job.method.value,
            "complexity": job.complexity,
            "model": job.model,
            "artifact": prepared.artifact.relative_path,
        })

        allowed = eligible_providers
        candidates = [
            adapter
            for adapter in adapters
            if adapter.supports(job)
            and adapter.credentials_available()
            and (allowed is None or adapter.info.name in allowed)
        ]
        snapshots = [await adapter.verify_research_quota() for adapter in candidates]
        ranked = self.guard.rank(snapshots, job)
        if not ranked:
            self._audit("experiment_rejected", {
                "experiment_id": job.experiment_id,
                "reason": "no eligible free platform",
            })
            raise ProviderUnavailable("no eligible free platform can serve this job")

        chosen = next(adapter for adapter in candidates if adapter.info.name == ranked[0])
        request = WorkloadRequest(
            task_id=job.experiment_id,
            capability=METHOD_CAPABILITY[job.method],
            description=job.title,
            artifact_refs=[prepared.artifact.relative_path],
            max_runtime_seconds=job.hardware.max_runtime_minutes * 60,
            metadata={
                "experiment_id": job.experiment_id,
                "method": job.method.value,
                "model": job.model,
                "complexity": job.complexity,
            },
        )
        if self.vault is not None:
            self.vault.assert_no_credentials(request.metadata)

        environment = await chosen.provision(request)
        await chosen.start(environment.external_id)
        self._audit("experiment_submitted", {
            "experiment_id": job.experiment_id,
            "provider": chosen.info.name,
            "external_id": environment.external_id,
        })
        return ResearchRun(
            job=job,
            provider=chosen.info.name,
            environment=environment,
            request=request,
            artifacts=[prepared.artifact],
        )

    async def collect(self, run: ResearchRun, adapter: ResearchPlatformAdapter) -> dict:  # type: ignore[type-arg]
        raw = await adapter.collect_results(run.environment.external_id)
        wrapped = wrap_research_output(raw, run.provider)
        artifact = self.store.put(
            artifact_key(run.job.experiment_id, ArtifactKind.RESULT, "result.json"),
            json.dumps(wrapped, sort_keys=True, indent=2).encode("utf-8"),
        )
        run.artifacts.append(artifact)
        run.results = wrapped
        self._audit("experiment_results_collected", {
            "experiment_id": run.job.experiment_id,
            "provider": run.provider,
            "artifact": artifact.relative_path,
        })
        return wrapped
