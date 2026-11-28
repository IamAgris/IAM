"""WP8 — measured capability profiles and model introspection (OD-41).

Selection uses recorded benchmark evidence, never the model's name or parameter
count. Profiles record what a model reliably does, where it fails and what
hardware it needs.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, Iterable, List

from .artifacts import ArtifactKind, ArtifactStore, artifact_key
from .base import ResearchError
from .benchmarks import BenchmarkResult


class UnknownModel(ResearchError):
    """No measured profile exists for the requested model."""


class NoCapableModel(ResearchError):
    """No candidate meets the measured score threshold for a task."""


@dataclass
class CapabilityProfile:
    model: str
    strengths: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
    hardware_min: Dict[str, object] = field(default_factory=dict)
    context_limit: int = 4096
    languages: List[str] = field(default_factory=list)
    known_failures: List[str] = field(default_factory=list)
    safety_limits: List[str] = field(default_factory=list)
    training_history: List[str] = field(default_factory=list)
    benchmarks: Dict[str, float] = field(default_factory=dict)
    task_scores: Dict[str, float] = field(default_factory=dict)
    confidence: str = "measured"
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def apply(self, result: BenchmarkResult) -> None:
        self.benchmarks[result.spec_name] = result.mean
        self.task_scores[result.task_type] = result.mean
        self.updated_at = datetime.now(timezone.utc).isoformat()
        if result.mean < 0.5:
            failure = f"{result.spec_name}: mean {result.mean}"
            if failure not in self.known_failures:
                self.known_failures.append(failure)

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class CapabilityRegistry:
    def __init__(self, store: ArtifactStore | None = None) -> None:
        self.store = store
        self._profiles: Dict[str, CapabilityProfile] = {}

    def record(self, result: BenchmarkResult, profile: CapabilityProfile | None = None) -> CapabilityProfile:
        entry = profile or self._profiles.get(result.model)
        if entry is None:
            entry = CapabilityProfile(model=result.model)
        entry.apply(result)
        self._profiles[result.model] = entry
        if self.store is not None:
            self.store.put(
                artifact_key(result.experiment_id, ArtifactKind.RESULT, "capability_profile.json"),
                json.dumps(entry.to_dict(), sort_keys=True, indent=2).encode("utf-8"),
            )
        return entry

    def profile(self, model: str) -> CapabilityProfile:
        if model not in self._profiles:
            raise UnknownModel(f"no measured capability profile for {model}")
        return self._profiles[model]

    def select(
        self, candidates: Iterable[str], task_type: str, min_score: float = 0.0
    ) -> str:
        """Pick the best model by measured capability for the requested task."""
        eligible = []
        for model in candidates:
            if model not in self._profiles:
                continue
            score = self._profiles[model].task_scores.get(task_type)
            if score is not None and score >= min_score:
                eligible.append((score, model))
        if not eligible:
            raise NoCapableModel(
                f"no measured model meets score {min_score} for {task_type}"
            )
        return max(eligible, key=lambda item: item[0])[1]
