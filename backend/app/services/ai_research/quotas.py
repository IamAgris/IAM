"""WP2 — GPU-aware free-tier quota model and fail-closed gate (OD-41).

Extends the Doc 22 quota contract with GPU capability, VRAM, session limits
and concurrency. There is no paid fallback: an ineligible platform is refused.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from ..free_sandboxes.base import FreeTierUnverified, QuotaExceeded, QuotaSnapshot
from ..free_sandboxes.quota import DEFAULT_SAFETY_MARGIN, QuotaGuard
from .base import PaidUpgradeRequested
from .jobs import ResearchJob


@dataclass
class ResearchQuotaSnapshot:
    provider: str
    used_percent: Optional[float] = None
    verified_at: Optional[str] = None
    source_url: Optional[str] = None
    gpu_name: str = ""
    gpu_capability: float = 0.0
    vram_mb: int = 0
    ram_mb: int = 0
    session_limit_minutes: int = 0
    concurrent_jobs_limit: int = 0
    paid_required: bool = False
    reason: Optional[str] = None

    @property
    def verified(self) -> bool:
        return (
            self.used_percent is not None
            and self.verified_at is not None
            and bool(self.source_url)
        )

    def to_base(self) -> QuotaSnapshot:
        return QuotaSnapshot(
            provider=self.provider,
            used_percent=self.used_percent,
            verified_at=self.verified_at,
            source_url=self.source_url,
            reason=self.reason,
        )


class ResearchQuotaGuard:
    def __init__(self, safety_margin: float = DEFAULT_SAFETY_MARGIN) -> None:
        self._guard = QuotaGuard(safety_margin)

    def assert_allowed(self, snapshot: ResearchQuotaSnapshot, job: ResearchJob) -> None:
        if snapshot.paid_required:
            raise PaidUpgradeRequested(
                f"{snapshot.provider}: paid compute or upgrade required — refused"
            )
        self._guard.assert_allowed(snapshot.to_base())

        required = job.hardware
        if required.gpu_required and snapshot.gpu_capability <= 0:
            raise FreeTierUnverified(f"{snapshot.provider}: no GPU advertised")
        if required.min_vram_mb > snapshot.vram_mb:
            raise QuotaExceeded(
                f"{snapshot.provider}: {snapshot.vram_mb} MB VRAM < "
                f"{required.min_vram_mb} MB required"
            )
        if required.min_ram_mb > snapshot.ram_mb:
            raise QuotaExceeded(
                f"{snapshot.provider}: {snapshot.ram_mb} MB RAM < "
                f"{required.min_ram_mb} MB required"
            )
        if required.min_gpu_capability > snapshot.gpu_capability:
            raise QuotaExceeded(
                f"{snapshot.provider}: GPU capability {snapshot.gpu_capability} < "
                f"{required.min_gpu_capability} required"
            )
        if required.max_runtime_minutes > snapshot.session_limit_minutes:
            raise QuotaExceeded(
                f"{snapshot.provider}: session limit {snapshot.session_limit_minutes} min < "
                f"{required.max_runtime_minutes} min required"
            )
        if snapshot.concurrent_jobs_limit < 1:
            raise QuotaExceeded(f"{snapshot.provider}: no concurrent job slots")

    def rank(
        self, snapshots: Iterable[ResearchQuotaSnapshot], job: ResearchJob
    ) -> List[str]:
        """Eligible providers, lowest usage first (VRAM breaks ties)."""
        eligible = []
        for snapshot in snapshots:
            try:
                self.assert_allowed(snapshot, job)
            except (FreeTierUnverified, QuotaExceeded, PaidUpgradeRequested):
                continue
            eligible.append(snapshot)
        return [
            s.provider
            for s in sorted(
                eligible, key=lambda s: (s.used_percent or 0, -s.vram_mb)
            )
        ]
