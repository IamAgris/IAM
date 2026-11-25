"""WP11 — autonomous job recovery without Creator prompts for routine work (OD-41)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from ..free_sandboxes.base import ProviderUnavailable, SandboxError
from .adapters import ResearchPlatformAdapter
from .coordinator import ResearchCoordinator, ResearchRun
from .jobs import ResearchJob

AuditSink = Callable[[str, Dict[str, Any]], None]


@dataclass
class RecoveryPolicy:
    max_attempts: int = 2
    checkpoint_resume: bool = True


@dataclass
class FailureRecord:
    provider: str
    error: str
    attempt: int
    recoverable: bool


class JobRecovery:
    """Retry on another eligible free platform; never fall back to paid compute."""

    def __init__(
        self,
        coordinator: ResearchCoordinator,
        policy: Optional[RecoveryPolicy] = None,
        audit_sink: Optional[AuditSink] = None,
    ) -> None:
        self.coordinator = coordinator
        self.policy = policy or RecoveryPolicy()
        self.audit_sink = audit_sink

    def _audit(self, event: str, details: Dict[str, Any]) -> None:
        if self.audit_sink:
            self.audit_sink(event, details)

    async def recover(
        self,
        job: ResearchJob,
        failed_provider: str,
        adapters: Iterable[ResearchPlatformAdapter],
        checkpoint_ref: Optional[str] = None,
    ) -> ResearchRun:
        failures: List[FailureRecord] = []
        excluded = {failed_provider}
        for attempt in range(1, self.policy.max_attempts + 1):
            candidates = [
                adapter
                for adapter in adapters
                if adapter.info.name not in excluded
                and adapter.supports(job)
                and adapter.credentials_available()
            ]
            if not candidates:
                break
            retry_job = ResearchJob.from_manifest(job.to_manifest())
            if checkpoint_ref and self.policy.checkpoint_resume:
                retry_job.metadata["resume_from_checkpoint"] = checkpoint_ref
            self._audit("recovery_attempt", {
                "experiment_id": job.experiment_id,
                "failed_provider": failed_provider,
                "provider": candidates[0].info.name,
                "attempt": attempt,
            })
            try:
                run = await self.coordinator.submit(retry_job, candidates)
            except (SandboxError, ProviderUnavailable) as exc:
                provider = candidates[0].info.name
                failures.append(FailureRecord(provider, str(exc)[:300], attempt, True))
                excluded.add(provider)
                self._audit("recovery_failed", {
                    "experiment_id": job.experiment_id,
                    "provider": provider,
                    "reason": str(exc)[:200],
                })
                continue
            self._audit("experiment_recovered", {
                "experiment_id": job.experiment_id,
                "from": failed_provider,
                "provider": run.provider,
                "attempt": attempt,
                "resumed": bool(checkpoint_ref),
            })
            return run
        raise ProviderUnavailable(
            f"recovery exhausted for {job.experiment_id}: "
            + "; ".join(f"{f.provider}:{f.error}" for f in failures)
        )
