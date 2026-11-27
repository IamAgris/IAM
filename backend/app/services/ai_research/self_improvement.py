"""Self-improvement orchestrator (OD-40/OD-41).

Links diagnosis -> dataset -> SFT/QLoRA job -> reproducible benchmark ->
registered candidate. It never promotes: the signed ``ModelReleaseService.promote``
gate and its serving bridge remain the only way a model becomes primary.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

from .artifacts import ArtifactKind, ArtifactStore, artifact_key
from .benchmarks import BenchmarkResult, BenchmarkRunner, BenchmarkSpec
from .coordinator import ResearchCoordinator
from .dataset_engine import DatasetBuildRequest, DatasetBuildResult, TRAINING_CONSENT_TYPES, build as build_dataset
from .base import InvalidResearchJob
from .jobs import HardwareRequirement, ResearchMethod
from .profiles import CapabilityRegistry
from .release_gate import ModelReleaseService, default_release_store
from .training import FineTuneSpec, TrainingService


@dataclass
class CandidateRequest:
    experiment_id: str
    licence: str
    base_model: str = settings.iam_primary_model
    version: str = "candidate"
    task_type: str = "coding"
    checkpoint_ref: str = ""
    baseline_score: float = 0.0
    min_improvement: float = 0.01
    min_confidence: float = 0.7
    max_rows: int = 200
    consent_types: frozenset[str] = TRAINING_CONSENT_TYPES
    private_markers: tuple[str, ...] = ()
    diagnosis: str = ""
    hardware: HardwareRequirement | None = None
    benchmark_spec: BenchmarkSpec | None = None


async def prepare_candidate(
    db: AsyncSession,
    request: CandidateRequest,
    *,
    store: ArtifactStore | None = None,
    adapters: Iterable[Any] = (),
    credentials: Iterable[Any] = (),
    evaluate: Optional[Callable[[BenchmarkSpec, str], float]] = None,
    actor: str = "iam",
) -> Dict[str, Any]:
    """Prepare a benchmarked candidate version. Never promotes it."""
    store = store or default_release_store()
    adapters = list(adapters)
    if not request.checkpoint_ref.strip():
        raise InvalidResearchJob("checkpoint_ref is required before benchmarking")
    if evaluate is None:
        raise InvalidResearchJob("a trusted evaluate callable is required")
    if not adapters:
        raise InvalidResearchJob("no eligible training adapter with a driver is configured")

    dataset: DatasetBuildResult = await build_dataset(
        db,
        DatasetBuildRequest(
            experiment_id=request.experiment_id,
            licence=request.licence,
            min_confidence=request.min_confidence,
            max_rows=request.max_rows,
            consent_types=request.consent_types,
            private_markers=request.private_markers,
            diagnosis=request.diagnosis,
        ),
        store=store,
    )

    spec = FineTuneSpec(
        experiment_id=request.experiment_id,
        base_model=request.base_model,
        dataset_ref=dataset.dataset_ref,
        method=ResearchMethod.QLORA,
        licence=dataset.licence,
        consent_recorded=dataset.consent_recorded,
        poisoning_scan_ref=dataset.poisoning_scan_ref,
        dataset_sha256=dataset.dataset_sha256,
        hardware=request.hardware or HardwareRequirement(
            min_ram_mb=4096, min_vram_mb=0, max_runtime_minutes=60
        ),
        notes=request.diagnosis[:1000],
    )
    spec.validate_provenance()

    coordinator = ResearchCoordinator(store)
    run, job = await TrainingService(coordinator, store).submit(
        spec, adapters, credentials, private_markers=request.private_markers
    )

    benchmark_spec = request.benchmark_spec or BenchmarkSpec(
        name=f"{request.task_type}-regression",
        task_type=request.task_type,
        repetitions=2,
    )
    runner = BenchmarkRunner(store)
    results: List[BenchmarkResult] = [
        runner.run(
            benchmark_spec,
            request.base_model,
            request.experiment_id,
            hardware={"checkpoint_ref": request.checkpoint_ref},
            evaluate=evaluate,
        )
        for _ in range(2)
    ]
    BenchmarkRunner.assert_reproducible(results[0], results[1])
    post_score = results[1].mean
    TrainingService.validate_improvement(
        request.baseline_score, post_score, request.min_improvement
    )

    profile = CapabilityRegistry(store).record(results[1]).to_dict()
    # Each run gets a distinct, immutable evidence artifact; the runner's own
    # key is overwritten by the second run, so copy both before registering.
    benchmark_refs: List[str] = []
    for index, result in enumerate(results, start=1):
        ref = artifact_key(
            request.experiment_id,
            ArtifactKind.BENCHMARK,
            f"{benchmark_spec.name}-run{index}.json",
        )
        store.put(
            ref,
            json.dumps(result.to_dict(), sort_keys=True, indent=2).encode("utf-8"),
            {"content_type": "application/json"},
        )
        benchmark_refs.append(ref)
    registered = await ModelReleaseService(db, store).register(
        model=request.base_model,
        version=request.version,
        checkpoint_ref=request.checkpoint_ref,
        capability_profile=profile,
        baseline_score=request.baseline_score,
        min_improvement=request.min_improvement,
        dataset_ref=dataset.dataset_ref,
        dataset_sha256=dataset.dataset_sha256,
        licence=dataset.licence,
        consent_recorded=dataset.consent_recorded,
        poisoning_scan_ref=dataset.poisoning_scan_ref,
        benchmark_ref=benchmark_refs[0],
        actor=actor,
    )
    return {
        "status": "candidate",
        "model": request.base_model,
        "version": request.version,
        "experiment_id": request.experiment_id,
        "dataset": dataset.as_dict(),
        "training_experiment": job.experiment_id,
        "benchmark_refs": benchmark_refs,
        "baseline_score": request.baseline_score,
        "post_score": post_score,
        "registered": registered,
        "promoted": False,
    }
