"""Fail-closed quota enforcement for free-tier resources (Doc 22 §3.8)."""

from __future__ import annotations

from typing import Iterable, List

from .base import FreeTierUnverified, QuotaExceeded, QuotaSnapshot

DEFAULT_SAFETY_MARGIN = 0.20  # refuse new work at 80% consumption


class QuotaGuard:
    """Enforces a safety margin and refuses unknown quota state.

    There is deliberately no paid fallback path: when a provider cannot be
    verified, the workload waits for a reset or another *free* provider.
    """

    def __init__(self, safety_margin: float = DEFAULT_SAFETY_MARGIN) -> None:
        if not 0 < safety_margin < 1:
            raise ValueError("safety_margin must be between 0 and 1")
        self.safety_margin = safety_margin

    @property
    def threshold_percent(self) -> float:
        return (1 - self.safety_margin) * 100

    def assert_allowed(self, snapshot: QuotaSnapshot) -> None:
        if not snapshot.verified:
            raise FreeTierUnverified(
                f"{snapshot.provider}: quota is unverified; refusing to provision"
            )
        if snapshot.used_percent is None or snapshot.used_percent >= self.threshold_percent:
            raise QuotaExceeded(
                f"{snapshot.provider}: usage {snapshot.used_percent}% has reached "
                f"the {self.threshold_percent:.0f}% free-tier safety threshold"
            )

    def rank(self, snapshots: Iterable[QuotaSnapshot]) -> List[str]:
        """Return eligible provider names, lowest usage first."""
        eligible = []
        for snapshot in snapshots:
            try:
                self.assert_allowed(snapshot)
            except (FreeTierUnverified, QuotaExceeded):
                continue
            eligible.append(snapshot)
        return [s.provider for s in sorted(eligible, key=lambda s: s.used_percent or 0)]
