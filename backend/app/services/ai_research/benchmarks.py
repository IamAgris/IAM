"""WP7 — reproducible benchmark runner for IAM models (OD-41).

Every result records the exact spec, config, hardware and evaluator so the same
experiment can be repeated and compared. External evaluation output is untrusted;
only numeric scores extracted by a trusted evaluator enter a capability profile.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Protocol

from ..free_sandboxes.results import redact
from .artifacts import ArtifactKind, ArtifactStore, artifact_key, sha256_bytes
from .base import ResearchError


class BenchmarkUnstable(ResearchError):
    """Repeated runs differ beyond the declared tolerance."""


class LMEvalDriver(Protocol):
    def evaluate(self, spec: "BenchmarkSpec", model: str) -> float: ...


@dataclass(frozen=True)
class BenchmarkSpec:
    name: str
    task_type: str  # coding, reasoning, safety, efficiency, ...
    metric: str = "accuracy"
    repetitions: int = 3
    tolerance_pct: float = 5.0
    score_min: float = 0.0
    score_max: float = 1.0
    evaluator: str = "custom"  # custom | lm_eval
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkResult:
    spec_name: str
    task_type: str
    model: str
    experiment_id: str
    scores: List[float]
    mean: float
    stdev: float
    config_hash: str
    hardware: Dict[str, Any]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BenchmarkRunner:
    """Runs custom or lm-evaluation-harness tasks and persists evidence."""

    def __init__(
        self,
        store: ArtifactStore,
        lm_eval_driver: Optional[LMEvalDriver] = None,
    ) -> None:
        self.store = store
        self.lm_eval_driver = lm_eval_driver

    def run(
        self,
        spec: BenchmarkSpec,
        model: str,
        experiment_id: str,
        hardware: Optional[Dict[str, Any]] = None,
        evaluate: Optional[Callable[[BenchmarkSpec, str], float]] = None,
    ) -> BenchmarkResult:
        if spec.repetitions < 1:
            raise ResearchError("benchmark repetitions must be >= 1")
        hardware = hardware or {}
        if spec.evaluator == "custom":
            if evaluate is None:
                raise ResearchError("custom benchmarks require an evaluate callable")
            evaluator = evaluate
        elif spec.evaluator == "lm_eval":
            if self.lm_eval_driver is None:
                raise ResearchError("lm_eval driver is not configured")
            evaluator = self.lm_eval_driver.evaluate
        else:
            raise ResearchError(f"unknown evaluator: {spec.evaluator}")

        scores: List[float] = []
        try:
            for _ in range(spec.repetitions):
                score = float(evaluator(spec, model))
                if not spec.score_min <= score <= spec.score_max:
                    raise ResearchError(
                        f"{spec.name}: score {score} outside "
                        f"[{spec.score_min}, {spec.score_max}]"
                    )
                scores.append(score)
        except Exception as exc:
            # Failed experiments are retained so IAM can learn from them.
            failure = {
                "status": "failed",
                "spec": asdict(spec),
                "model": model,
                "experiment_id": experiment_id,
                "hardware": hardware,
                "error": redact(str(exc))[:500],
                "completed_scores": scores,
            }
            self.store.put(
                artifact_key(
                    experiment_id,
                    ArtifactKind.BENCHMARK,
                    f"{spec.name}.failed.json",
                ),
                json.dumps(failure, sort_keys=True, indent=2).encode("utf-8"),
            )
            raise

        fingerprint = {
            "spec": asdict(spec),
            "model": model,
            "hardware": hardware,
        }
        config_hash = sha256_bytes(
            json.dumps(fingerprint, sort_keys=True, default=str).encode("utf-8")
        )
        result = BenchmarkResult(
            spec_name=spec.name,
            task_type=spec.task_type,
            model=model,
            experiment_id=experiment_id,
            scores=scores,
            mean=round(statistics.mean(scores), 6),
            stdev=round(statistics.stdev(scores), 6) if len(scores) > 1 else 0.0,
            config_hash=config_hash,
            hardware=hardware,
        )
        self.store.put(
            artifact_key(experiment_id, ArtifactKind.BENCHMARK, f"{spec.name}.json"),
            json.dumps(result.to_dict(), sort_keys=True, indent=2).encode("utf-8"),
        )
        return result

    @staticmethod
    def assert_reproducible(
        first: BenchmarkResult, second: BenchmarkResult, tolerance_pct: Optional[float] = None
    ) -> None:
        if first.config_hash != second.config_hash:
            raise BenchmarkUnstable("benchmark config/hardware differs between runs")
        tolerance = tolerance_pct if tolerance_pct is not None else 5.0
        baseline = abs(first.mean) or 1.0
        delta_pct = 100 * abs(first.mean - second.mean) / baseline
        if delta_pct > tolerance:
            raise BenchmarkUnstable(
                f"repeated scores differ by {delta_pct:.1f}% (> {tolerance}%)"
            )
