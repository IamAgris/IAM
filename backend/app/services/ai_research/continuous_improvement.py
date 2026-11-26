"""OD-41 continuous-improvement loop over the existing research services.

A failed experiment's diagnosis is retained in ResearchMemory, fed into the
next job's metadata, scheduled via PlatformLifecycle + ResearchScheduler,
recovered on another free platform, then written back as a ReflectionEntry and
CapabilityAssessment. No paid compute, external credentials or new tables.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.capability import CapabilityAssessment, CapabilityDefinition
from app.models.reflection import ReflectionEntry
from app.services.ai_research.adapters import (
    ColabResearchAdapter,
    HuggingFaceResearchAdapter,
    KaggleResearchAdapter,
    LightningAIResearchAdapter,
)
from app.services.ai_research.artifacts import FileSystemArtifactStore
from app.services.ai_research.coordinator import ResearchCoordinator
from app.services.ai_research.jobs import ResearchJob
from app.services.ai_research.lifecycle import PlatformLifecycle
from app.services.ai_research.memory import ExperimentRecord, ResearchMemory
from app.services.ai_research.recovery import JobRecovery
from app.services.ai_research.scheduler import ResearchScheduler, WorkloadProfile
from app.services.free_sandboxes.base import ProviderUnavailable, SandboxError


@dataclass
class ContinuousRunResult:
    experiment_id: str
    provider: str
    status: str
    score: float
    diagnosis: str
    evidence_ref: str
    recovered_from: Optional[str] = None
    reflection_id: Optional[str] = None
    capability_id: Optional[str] = None
    prior_failures: List[str] = field(default_factory=list)
    avoided_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "provider": self.provider,
            "status": self.status,
            "score": self.score,
            "diagnosis": self.diagnosis,
            "evidence_ref": self.evidence_ref,
            "recovered_from": self.recovered_from,
            "reflection_id": self.reflection_id,
            "capability_id": self.capability_id,
            "prior_failures": self.prior_failures,
            "avoided_tags": self.avoided_tags,
        }


def default_store() -> FileSystemArtifactStore:
    root = settings.model_release_artifact_root or str(
        Path(tempfile.gettempdir()) / "iam-research-continuity"
    )
    return FileSystemArtifactStore(root)


def default_adapters():
    return [
        ColabResearchAdapter(),
        KaggleResearchAdapter(),
        LightningAIResearchAdapter(),
        HuggingFaceResearchAdapter(),
    ]


class ContinuousImprovement:
    def __init__(
        self,
        db: AsyncSession,
        store=None,
        adapters=None,
        audit_sink=None,
    ):
        self.db = db
        self.store = store or default_store()
        self.adapters = list(adapters or default_adapters())
        self.audit_sink = audit_sink
        events: List[Dict[str, Any]] = []

        def sink(event: str, details: Dict[str, Any]) -> None:
            events.append({"event": event, "details": details})
            if audit_sink:
                audit_sink(event, details)

        self.events = events
        self.coordinator = ResearchCoordinator(self.store, audit_sink=sink)
        self.memory = ResearchMemory(self.store)
        self.memory.hydrate()
        self.scheduler = ResearchScheduler()
        self.lifecycle = PlatformLifecycle()
        self.recovery = JobRecovery(self.coordinator, audit_sink=sink)

    def _adapter(self, name: str):
        return next(item for item in self.adapters if item.info.name == name)

    async def _schedule(self, job: ResearchJob) -> List[str]:
        await self.lifecycle.monitor(self.adapters)
        eligible = set(self.lifecycle.eligible())
        candidates = [item for item in self.adapters if item.info.name in eligible]
        snapshots = [await item.verify_research_quota() for item in candidates]
        profile = WorkloadProfile(
            ram_mb=job.hardware.min_ram_mb,
            vram_mb=job.hardware.min_vram_mb,
            gpu_capability=job.hardware.min_gpu_capability,
            runtime_minutes=job.hardware.max_runtime_minutes,
            complexity=job.complexity,
        )
        decisions = self.scheduler.rank(candidates, snapshots, profile)
        return [decision.provider for decision in decisions if decision.score >= 0]

    async def _capability(self, task_type: str, score: float, evidence: str) -> str:
        name = task_type or "research"
        result = await self.db.execute(
            select(CapabilityDefinition).where(CapabilityDefinition.name == name)
        )
        definition = result.scalar_one_or_none()
        if not definition:
            definition = CapabilityDefinition(
                name=name,
                category="science",
                description="Measured through IAM's autonomous research loop",
                is_learnable=True,
            )
            self.db.add(definition)
            await self.db.flush()
        self.db.add(
            CapabilityAssessment(
                capability_id=definition.id,
                proficiency_level=max(0, min(100, int(score * 100))),
                assessment_method="automated",
                evidence=[evidence],
                assessor="self",
            )
        )
        return str(definition.id)

    async def run(self, job: ResearchJob, actor: str = "iam") -> ContinuousRunResult:
        suggestion = self.memory.suggest_next(job.task_type)
        metadata = dict(job.metadata or {})
        metadata["continuous_improvement"] = {
            "from_failures": suggestion["from_failures"],
            "avoid": suggestion["avoid"],
            "reuse": suggestion["reuse"],
            "diagnoses": suggestion["diagnoses"],
        }
        job.metadata = metadata

        providers = await self._schedule(job)
        if not providers:
            raise ProviderUnavailable("no eligible free research platform")

        recovered_from = None
        try:
            run = await self.coordinator.submit(
                job,
                [self._adapter(name) for name in providers],
                eligible_providers=set(providers),
            )
        except (SandboxError, ProviderUnavailable) as exc:
            run = await self.recovery.recover(
                job,
                providers[0],
                [self._adapter(name) for name in providers],
            )
            recovered_from = providers[0]

        adapter = self._adapter(run.provider)
        wrapped = await self.coordinator.collect(run, adapter)
        evidence = next(
            (
                artifact.relative_path
                for artifact in reversed(run.artifacts)
                if artifact.relative_path.endswith("result.json")
            ),
            "",
        )
        content = wrapped.get("content", wrapped) if isinstance(wrapped, dict) else {}
        if not isinstance(content, dict):
            content = {}
        raw_score = content.get("score", 0)
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 0.0
        succeeded = content.get("status") == "completed"
        diagnosis = ""
        if not succeeded:
            diagnosis = str(
                content.get("reason") or content.get("error") or "experiment did not complete"
            )

        self.memory.record(
            ExperimentRecord(
                experiment_id=job.experiment_id,
                task_type=job.task_type,
                method=job.method.value,
                score=score,
                succeeded=succeeded,
                diagnosis=diagnosis,
                tags=[job.model],
            )
        )

        reflection = ReflectionEntry(
            reflection_type="outcome",
            title=f"Research outcome: {job.experiment_id}",
            content=f"provider={run.provider}; score={score}; status={content.get('status')}",
            lesson_learned=(
                diagnosis
                if diagnosis
                else f"Measured score {score}; prior failures: {suggestion['from_failures']}"
            ),
            confidence=0.5,
        )
        self.db.add(reflection)
        await self.db.flush()
        capability_id = await self._capability(job.task_type, score, evidence)
        await self.db.commit()

        return ContinuousRunResult(
            experiment_id=job.experiment_id,
            provider=run.provider,
            status="completed" if succeeded else "failed",
            score=score,
            diagnosis=diagnosis,
            evidence_ref=evidence,
            recovered_from=recovered_from,
            reflection_id=str(reflection.id),
            capability_id=capability_id,
            prior_failures=list(suggestion["from_failures"]),
            avoided_tags=list(suggestion["avoid"]),
        )

    async def history(self) -> List[Dict[str, Any]]:
        return [entry.to_dict() for entry in self.memory._records.values()]
