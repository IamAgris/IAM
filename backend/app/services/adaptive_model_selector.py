"""Adaptive model selection — hardware-aware local model choice (OD-39 / OD-41).

Picks the smallest local model that can handle the task within available RAM,
and delegates to an authorised hosted specialist or trusted node when no local
model fits. Does not pool RAM across machines and never exceeds the protected
core-service reserve.

Usage:
    selector = AdaptiveModelSelector()
    decision = selector.select(task_complexity=3, available_aliases={"local-qwen-coder-3b"})
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Set

from app.core.config import settings


@dataclass(frozen=True)
class ResourceSnapshot:
    total_ram_mb: int
    available_ram_mb: int
    cpu_count: int
    has_gpu: bool
    source: str = "auto"


@dataclass(frozen=True)
class ModelTier:
    name: str
    alias: str
    min_ram_mb: int
    max_complexity: int
    context_tokens: int


def _read_int(path: str) -> Optional[int]:
    try:
        value = Path(path).read_text(encoding="utf-8").strip()
        return int(value) if value.isdigit() else None
    except (OSError, ValueError):
        return None


def detect_resources() -> ResourceSnapshot:
    """Detect host RAM and respect the container's cgroup memory ceiling."""
    total_mb, available_mb = 8192, 4096
    try:
        meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
        total_kb = int(re.search(r"MemTotal:\s+(\d+) kB", meminfo).group(1))
        free_kb = int(re.search(r"MemAvailable:\s+(\d+) kB", meminfo).group(1))
        total_mb, available_mb = total_kb // 1024, free_kb // 1024
    except (OSError, AttributeError, ValueError):
        pass

    limit = _read_int("/sys/fs/cgroup/memory.max")
    current = _read_int("/sys/fs/cgroup/memory.current")
    if limit and current is not None:
        total_mb = min(total_mb, limit // 2**20)
        available_mb = min(available_mb, max(0, (limit - current) // 2**20))

    gpu = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    return ResourceSnapshot(
        total_ram_mb=total_mb,
        available_ram_mb=available_mb,
        cpu_count=os.cpu_count() or 1,
        has_gpu=bool(gpu and gpu != "-1"),
    )


class AdaptiveModelSelector:
    """Select a local model by task complexity and usable RAM."""

    def __init__(self, snapshot: Optional[ResourceSnapshot] = None):
        self.snapshot = snapshot or detect_resources()
        self.tiers = [
            ModelTier("0.5b", settings.adaptive_tiny_model, 0, 1, 1024),
            ModelTier("1.5b", settings.adaptive_small_model, 800, 2, 2048),
            ModelTier("3b", settings.adaptive_standard_model,
                      settings.adaptive_min_ram_mb_standard, 3, 4096),
            ModelTier("7b", settings.adaptive_large_model,
                      settings.adaptive_min_ram_mb_large, 4, 4096),
        ]

    @property
    def usable_ram_mb(self) -> int:
        """RAM left for the model after the essential-services reserve."""
        return max(0, self.snapshot.available_ram_mb - settings.adaptive_reserved_ram_mb)

    def select(
        self,
        task_complexity: int,
        available_aliases: Set[str],
        task_type: str = "conversation",
    ) -> dict:
        """Return a routing decision dict.

        task_complexity: 1 simple text, 2 light coding, 3 regular coding,
        4 complex coding, 5+ requires a hosted specialist / trusted node.
        """
        task_complexity = max(1, int(task_complexity))
        candidates = [
            tier
            for tier in self.tiers
            if tier.alias in available_aliases
            and tier.max_complexity >= task_complexity
            and tier.min_ram_mb <= self.usable_ram_mb
        ]
        if candidates:
            tier = min(candidates, key=lambda t: t.min_ram_mb)
            return {
                "model": tier.alias,
                "tier": tier.name,
                "delegate": False,
                "context_tokens": tier.context_tokens,
                "max_concurrent": 1,
                "reason": (
                    f"Adaptive selection: {tier.name} handles complexity "
                    f"{task_complexity} within {self.usable_ram_mb} MB usable RAM"
                ),
                "task_type": task_type,
            }

        hardest_local = max((t.max_complexity for t in self.tiers), default=0)
        reason = (
            "Task exceeds local model capability"
            if task_complexity > hardest_local
            else "No local model fits the available RAM"
        )
        return {
            "model": settings.adaptive_delegate_model,
            "tier": "delegated",
            "delegate": True,
            "delegate_node": settings.adaptive_delegate_node,
            "context_tokens": None,
            "max_concurrent": 1,
            "reason": f"{reason}; delegating to an authorised specialist",
            "task_type": task_type,
        }

    @staticmethod
    def unload(model_alias: str) -> bool:
        """Ask Ollama to release a model (keep_alive=0). Best-effort."""
        try:
            body = json.dumps(
                {"model": model_alias, "prompt": "", "keep_alive": 0}
            ).encode("utf-8")
            req = urllib.request.Request(
                f"{settings.ollama_base_url}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception:
            return False
