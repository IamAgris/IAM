"""WP12 — workload-aware free-platform scheduling (OD-41).

Selects platforms by GPU capability, VRAM/RAM fit, session length, quota state
and declared preference — not merely by lowest usage. Eligibility is still
enforced by the fail-closed quota guard.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from ..free_sandboxes.base import FreeTierUnverified, QuotaExceeded
from .adapters import ResearchPlatformAdapter
from .base import PaidUpgradeRequested
from .quotas import ResearchQuotaGuard, ResearchQuotaSnapshot


@dataclass(frozen=True)
class WorkloadProfile:
    vram_mb: int = 0
    ram_mb: int = 4096
    gpu_capability: float = 0.0
    runtime_minutes: int = 60
    complexity: int = 3
    prefer_provider: str = ""


@dataclass(frozen=True)
class SchedulingDecision:
    provider: str
    score: float
    reason: str


class ResearchScheduler:
    def __init__(self, guard: Optional[ResearchQuotaGuard] = None) -> None:
        self.guard = guard or ResearchQuotaGuard()

    def rank(
        self,
        adapters: Iterable[ResearchPlatformAdapter],
        snapshots: Iterable[ResearchQuotaSnapshot],
        profile: WorkloadProfile,
    ) -> List[SchedulingDecision]:
        quotas = {snapshot.provider: snapshot for snapshot in snapshots}
        decisions: List[SchedulingDecision] = []
        for adapter in adapters:
            name = adapter.info.name
            snapshot = quotas.get(name)
            if snapshot is None:
                continue
            try:
                self.guard.assert_allowed(snapshot, self._as_job(snapshot, profile))
            except (FreeTierUnverified, QuotaExceeded, PaidUpgradeRequested) as exc:
                decisions.append(SchedulingDecision(name, -1.0, f"ineligible: {exc}"))
                continue

            score = 100.0 - (snapshot.used_percent or 0)
            score += min(snapshot.vram_mb - profile.vram_mb, 8000) / 100
            if profile.gpu_capability and name == profile.prefer_provider:
                score += 10
            decisions.append(
                SchedulingDecision(
                    name,
                    round(score, 2),
                    f"quota {snapshot.used_percent}%, "
                    f"GPU {snapshot.gpu_name or 'none'} ({snapshot.gpu_capability}), "
                    f"VRAM {snapshot.vram_mb} MB, session {snapshot.session_limit_minutes} min",
                )
            )
        return sorted(decisions, key=lambda d: d.score, reverse=True)

    @staticmethod
    def _as_job(snapshot: ResearchQuotaSnapshot, profile: WorkloadProfile):  # type: ignore[no-untyped-def]
        # Reuse the quota guard by translating the workload into a minimal job.
        from .jobs import HardwareRequirement, ResearchJob, ResearchMethod

        return ResearchJob(
            experiment_id="scheduling-probe",
            title="scheduling",
            task_type="scheduling",
            complexity=profile.complexity,
            method=ResearchMethod.EVALUATION,
            model="probe",
            hardware=HardwareRequirement(
                min_ram_mb=profile.ram_mb,
                min_vram_mb=profile.vram_mb,
                min_gpu_capability=profile.gpu_capability,
                max_runtime_minutes=profile.runtime_minutes,
                gpu_required=profile.gpu_capability > 0,
            ),
        )

    def best(
        self,
        adapters: Iterable[ResearchPlatformAdapter],
        snapshots: Iterable[ResearchQuotaSnapshot],
        profile: WorkloadProfile,
    ) -> Optional[SchedulingDecision]:
        ranked = self.rank(adapters, snapshots, profile)
        return ranked[0] if ranked and ranked[0].score >= 0 else None
