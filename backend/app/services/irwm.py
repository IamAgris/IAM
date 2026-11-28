"""Intelligent Resource and Workload Manager (OD-39).

Runtime enforcement of the 8 GB core policy: at most one resident model, at
most one concurrent request, a hard loaded-model ceiling, a short keep-alive,
and a bounded context. Core services are never evicted to keep a model loaded.
State is per-process; multi-replica coordination is a deployment concern.
"""

import asyncio
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

from app.core.config import settings
from app.services.adaptive_model_selector import ResourceSnapshot, detect_resources


@dataclass
class Lease:
    admitted_at: float
    purpose: str = "internal"
    preemptible: bool = True
    task: Any = None


@dataclass
class Residency:
    model: str
    estimated_ram_mb: int
    context_tokens: int
    loaded_at: float
    last_used: float
    in_flight: int = 0
    in_flight_since: Optional[float] = None  # set when in_flight goes 0 -> 1
    leases: Dict[str, Lease] = field(default_factory=dict)


class IRWM:
    def __init__(
        self,
        snapshot: Optional[ResourceSnapshot] = None,
        unloader: Optional[Callable[[str], bool]] = None,
    ):
        self._snapshot_fixed = snapshot is not None  # injected snapshots are authoritative
        self.snapshot = snapshot or detect_resources()
        self._snapshot_at = time.monotonic()
        self.unloader = unloader
        self.resident: Optional[Residency] = None
        self.queue: Deque[Dict[str, Any]] = deque(maxlen=256)
        self.history: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._lock = asyncio.Lock()

    def _live_snapshot(self) -> ResourceSnapshot:
        """Re-read host/cgroup memory for auto-detected snapshots.

        A snapshot frozen at import can keep the primary permanently delegated
        after a temporary memory spike. Tests and operators that inject an
        explicit snapshot keep their deterministic reading.
        """
        if not self._snapshot_fixed:
            self.snapshot = detect_resources()
            self._snapshot_at = time.monotonic()
        return self.snapshot

    @property
    def usable_ram_mb(self) -> int:
        return max(
            0, self._live_snapshot().available_ram_mb - settings.adaptive_reserved_ram_mb
        )

    def _unload(self, model: str) -> bool:
        if not self.unloader:
            return False
        try:
            return bool(self.unloader(model))
        except Exception:
            return False

    def sweep_idle(self) -> Optional[str]:
        """Release an idle resident, and expire stuck in-flight leases.

        A lease can leak if a request is interrupted without a release, or if a
        caller admits directly through the admin route. Stuck slots are expired
        after ``irwm_in_flight_timeout_seconds`` so the gateway cannot be
        permanently blocked by one stale request.
        """
        if not self.resident:
            return None
        if self.resident.in_flight:
            since = self.resident.in_flight_since or self.resident.last_used
            timeout = getattr(settings, "irwm_in_flight_timeout_seconds", 120)
            if time.monotonic() - since > timeout:
                model = self.resident.model
                self.history.append({
                    "decision": "expired_in_flight", "model": model,
                    "reason": "lease exceeded timeout without release",
                })
                self.resident.in_flight = 0
                self.resident.leases.clear()
                self.resident.in_flight_since = None
                self.resident.last_used = time.monotonic()
            else:
                return None
        idle = time.monotonic() - self.resident.last_used
        if idle < settings.irwm_keep_alive_seconds:
            return None
        model = self.resident.model
        self._unload(model)
        self.resident = None
        self.history.append({"decision": "unloaded_idle", "model": model})
        return model

    async def admit(
        self,
        model: str,
        estimated_ram_mb: int,
        context_tokens: Optional[int] = None,
        task_complexity: int = 3,
        enqueue: bool = True,
        purpose: str = "internal",
        preemptible: bool = True,
        task: Any = None,
    ) -> Dict[str, Any]:
        """Admit, queue or delegate a request without breaking the core reserve."""
        async with self._lock:
            self.sweep_idle()
            requested_context = min(
                context_tokens or settings.irwm_context_tokens,
                settings.irwm_context_tokens,
            )
            base = {
                "model": model,
                "context_tokens": requested_context,
                "task_complexity": task_complexity,
                "resident_model": self.resident.model if self.resident else None,
                "queue_depth": len(self.queue),
            }

            if estimated_ram_mb > settings.irwm_hard_ceiling_mb or estimated_ram_mb > self.usable_ram_mb:
                decision = {
                    **base,
                    "decision": "delegate",
                    "reason": "model exceeds the hard ceiling or core-service RAM reserve",
                }
                self.history.append(decision)
                return decision

            if self.resident and self.resident.model != model:
                if self.resident.in_flight:
                    if enqueue:
                        self.queue.append(
                            {"model": model, "estimated_ram_mb": estimated_ram_mb}
                        )
                    base["queue_depth"] = len(self.queue)
                    decision = {
                        **base,
                        "decision": "queue",
                        "reason": "another model is busy; request queued instead of evicting it",
                    }
                    self.history.append(decision)
                    return decision
                self._unload(self.resident.model)
                self.resident = None

            if not self.resident:
                now = time.monotonic()
                self.resident = Residency(
                    model=model,
                    estimated_ram_mb=estimated_ram_mb,
                    context_tokens=requested_context,
                    loaded_at=now,
                    last_used=now,
                )

            if (
                purpose == "user"
                and self.resident.in_flight
                and all(lease.preemptible for lease in self.resident.leases.values())
            ):
                # A user chat outranks internal background work. Cancel the
                # internal task(s) and reclaim the single residency slot rather
                # than refusing the user. The cancelled tasks' token releases
                # are no-ops because their leases are removed here.
                for lease in self.resident.leases.values():
                    if lease.task is not None and not lease.task.done():
                        lease.task.cancel()
                cancelled = len(self.resident.leases)
                self.resident.leases.clear()
                self.resident.in_flight = 0
                self.resident.in_flight_since = None
                self.history.append(
                    {
                        "decision": "preempted_internal",
                        "model": self.resident.model,
                        "cancelled": cancelled,
                    }
                )

            if self.resident.in_flight >= settings.irwm_max_concurrent:
                if enqueue:
                    self.queue.append(
                        {"model": model, "estimated_ram_mb": estimated_ram_mb}
                    )
                base["queue_depth"] = len(self.queue)
                decision = {
                    **base,
                    "decision": "queue",
                    "reason": "one resident request already in flight",
                }
                self.history.append(decision)
                return decision

            if self.resident.in_flight == 0:
                self.resident.in_flight_since = time.monotonic()
            lease_id = uuid.uuid4().hex
            self.resident.leases[lease_id] = Lease(
                admitted_at=time.monotonic(),
                purpose=purpose,
                preemptible=preemptible,
                task=task,
            )
            self.resident.in_flight = len(self.resident.leases)
            self.resident.last_used = time.monotonic()
            decision = {
                **base,
                "decision": "admit",
                "resident_model": self.resident.model,
                "reason": "model fits within the core-service reserve and concurrency limit",
                "lease_id": lease_id,  # idempotent release even after task cancellation
            }
            self.history.append(decision)
            return decision

    async def release(self, model: str, lease_id: Optional[str] = None) -> Dict[str, Any]:
        """Release one lease. Repeated releases of the same lease are harmless."""
        async with self._lock:
            if not self.resident or self.resident.model != model:
                return {"released": False, "reason": "model is not resident"}
            if lease_id is not None:
                if lease_id not in self.resident.leases:
                    return {
                        "released": False,
                        "reason": "lease already released",
                        "model": model,
                    }
                self.resident.leases.pop(lease_id, None)
                self.resident.in_flight = len(self.resident.leases)
            else:
                # Legacy callers (admin route, older tests) release one anonymous slot.
                if self.resident.leases:
                    self.resident.leases.pop(next(iter(self.resident.leases)))
                self.resident.in_flight = max(0, self.resident.in_flight - 1)
            if self.resident.in_flight == 0:
                self.resident.leases.clear()
                self.resident.in_flight_since = None
            self.resident.last_used = time.monotonic()
            promoted = None
            if not self.resident.in_flight and self.queue:
                promoted = self.queue.popleft()
            self.history.append(
                {"decision": "released", "model": model, "promoted": promoted}
            )
            return {"released": True, "model": model, "promoted": promoted}

    def status(self) -> Dict[str, Any]:
        self.sweep_idle()
        live = self._live_snapshot()
        return {
            "enabled": settings.irwm_enabled,
            "snapshot": {
                "total_ram_mb": live.total_ram_mb,
                "available_ram_mb": live.available_ram_mb,
                "cpu_count": live.cpu_count,
                "has_gpu": live.has_gpu,
                "source": live.source,
            },
            "usable_ram_mb": self.usable_ram_mb,
            "resident": (
                {
                    "model": self.resident.model,
                    "estimated_ram_mb": self.resident.estimated_ram_mb,
                    "context_tokens": self.resident.context_tokens,
                    "in_flight": self.resident.in_flight,
                    "leases": len(self.resident.leases),
                    "lease_age_s": (
                        round(
                            min(
                                time.monotonic() - lease.admitted_at
                                for lease in self.resident.leases.values()
                            ),
                            1,
                        )
                        if self.resident.leases
                        else 0
                    ),
                }
                if self.resident
                else None
            ),
            "queue_depth": len(self.queue),
            "limits": {
                "hard_ceiling_mb": settings.irwm_hard_ceiling_mb,
                "max_concurrent": settings.irwm_max_concurrent,
                "keep_alive_seconds": settings.irwm_keep_alive_seconds,
                "context_tokens": settings.irwm_context_tokens,
            },
            "recent_decisions": list(self.history)[-20:],
        }


irwm = IRWM()
