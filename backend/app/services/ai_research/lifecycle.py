"""WP13 — free-platform discovery, monitoring and retirement (OD-41)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from .adapters import ResearchPlatformAdapter
from .quotas import ResearchQuotaSnapshot

ACTIVE = "active"
DEGRADED = "degraded"
RETIRED = "retired"
DISCOVERED = "discovered"


@dataclass
class PlatformRecord:
    name: str
    state: str = DISCOVERED
    degraded_count: int = 0
    last_checked: Optional[str] = None
    reason: str = ""
    quota_history: List[dict] = field(default_factory=list)  # type: ignore[type-arg]


class PlatformLifecycle:
    def __init__(
        self, degraded_threshold_percent: float = 80.0, retire_after: int = 3
    ) -> None:
        self.degraded_threshold = degraded_threshold_percent
        self.retire_after = retire_after
        self._records: Dict[str, PlatformRecord] = {}

    def discover(self, adapters: Iterable[ResearchPlatformAdapter]) -> List[str]:
        names = []
        for adapter in adapters:
            name = adapter.info.name
            if name not in self._records:
                self._records[name] = PlatformRecord(name=name)
            names.append(name)
        return names

    async def monitor(self, adapters: Iterable[ResearchPlatformAdapter]) -> Dict[str, str]:
        """Refresh quota state from providers and mark degraded/retired platforms."""
        self.discover(adapters)
        for adapter in adapters:
            record = self._records[adapter.info.name]
            if record.state == RETIRED:
                continue
            snapshot: ResearchQuotaSnapshot = await adapter.verify_research_quota()
            record.last_checked = datetime.now(timezone.utc).isoformat()
            record.quota_history.append({
                "checked_at": record.last_checked,
                "used_percent": snapshot.used_percent,
                "verified": snapshot.verified,
                "paid_required": snapshot.paid_required,
            })
            unhealthy = (
                snapshot.paid_required
                or not snapshot.verified
                or (snapshot.used_percent or 0) >= self.degraded_threshold
            )
            if unhealthy:
                record.degraded_count += 1
                record.state = (
                    RETIRED if record.degraded_count >= self.retire_after else DEGRADED
                )
                record.reason = (
                    "paid compute required"
                    if snapshot.paid_required
                    else "quota unverified or exhausted"
                )
            else:
                record.degraded_count = 0
                record.state = ACTIVE
                record.reason = ""
        return {name: record.state for name, record in self._records.items()}

    def eligible(self) -> List[str]:
        return [name for name, record in self._records.items() if record.state == ACTIVE]

    def revalidate(self, name: str, snapshot: ResearchQuotaSnapshot) -> None:
        """Return a degraded platform to active service after fresh verification."""
        if not snapshot.verified or snapshot.paid_required:
            raise ValueError(f"{name}: cannot revalidate with unverified/paid quota")
        record = self._records[name]
        record.state = ACTIVE
        record.degraded_count = 0
        record.reason = ""
        record.last_checked = datetime.now(timezone.utc).isoformat()

    def record(self, name: str) -> PlatformRecord:
        return self._records[name]
