"""Intelligent Resource and Workload Manager (OD-39).

Runtime enforcement of the 8 GB core policy: at most one resident model, at
most one concurrent request, a hard loaded-model ceiling, a short keep-alive,
and a bounded context. Core services are never evicted to keep a model loaded.
State is per-process; multi-replica coordination is a deployment concern.
"""

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Deque, Dict, List, Optional

from app.core.config import settings
from app.services.adaptive_model_selector import ResourceSnapshot, detect_resources


@dataclass
class Residency:
    model: str
    estimated_ram_mb: int
    context_tokens: int
    loaded_at: float
    last_used: float
    in_flight: int = 0


class IRWM:
    def __init__(
        self,
        snapshot: Optional[ResourceSnapshot] = None,
        unloader: Optional[Callable[[str], bool]] = None,
    ):
        self.snapshot = snapshot or detect_resources()
        self.unloader = unloader
        self.resident: Optional[Residency] = None
        self.queue: Deque[Dict[str, Any]] = deque(maxlen=256)
        self.history: Deque[Dict[str, Any]] = deque(maxlen=200)
        self._lock = asyncio.Lock()

    @property
    def usable_ram_mb(self) -> int:
        return max(0, self.snapshot.available_ram_mb - settings.adaptive_reserved_ram_mb)

    def _unload(self, model: str) -> bool:
        if not self.unloader:
            return False
        try:
            return bool(self.unloader(model))
        except Exception:
            return False

    def sweep_idle(self) -> Optional[str]:
        """Release an idle resident after its keep-alive window."""
        if not self.resident or self.resident.in_flight:
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
                    self.queue.append({"model": model, "estimated_ram_mb": estimated_ram_mb})
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

            if self.resident.in_flight >= settings.irwm_max_concurrent:
                self.queue.append({"model": model, "estimated_ram_mb": estimated_ram_mb})
                base["queue_depth"] = len(self.queue)
                decision = {
                    **base,
                    "decision": "queue",
                    "reason": "one resident request already in flight",
                }
                self.history.append(decision)
                return decision

            self.resident.in_flight += 1
            self.resident.last_used = time.monotonic()
            decision = {
                **base,
                "decision": "admit",
                "resident_model": self.resident.model,
                "reason": "model fits within the core-service reserve and concurrency limit",
            }
            self.history.append(decision)
            return decision

    async def release(self, model: str) -> Dict[str, Any]:
        async with self._lock:
            if not self.resident or self.resident.model != model:
                return {"released": False, "reason": "model is not resident"}
            self.resident.in_flight = max(0, self.resident.in_flight - 1)
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
        return {
            "enabled": settings.irwm_enabled,
            "snapshot": {
                "total_ram_mb": self.snapshot.total_ram_mb,
                "available_ram_mb": self.snapshot.available_ram_mb,
                "cpu_count": self.snapshot.cpu_count,
                "has_gpu": self.snapshot.has_gpu,
                "source": self.snapshot.source,
            },
            "usable_ram_mb": self.usable_ram_mb,
            "resident": (
                {
                    "model": self.resident.model,
                    "estimated_ram_mb": self.resident.estimated_ram_mb,
                    "context_tokens": self.resident.context_tokens,
                    "in_flight": self.resident.in_flight,
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
