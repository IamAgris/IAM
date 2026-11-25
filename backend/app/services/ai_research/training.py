"""WP10 — SFT / QLoRA training jobs and quality gates (OD-41).

Training infrastructure stays framework-independent: this module builds the
common job spec, submits it through the coordinator, and gates deployment on a
measured comparison with the recorded baseline. No substantial training is run
on the 8 GB core.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional

from .artifacts import ArtifactKind, ArtifactStore, artifact_key
from .base import InvalidResearchJob, NoImprovement
from .coordinator import ResearchCoordinator, ResearchRun
from .credentials import CredentialRef
from .jobs import HardwareRequirement, ResearchJob, ResearchMethod
from .adapters import ResearchPlatformAdapter

TRAINING_METHODS = {
    ResearchMethod.SFT,
    ResearchMethod.LORA,
    ResearchMethod.QLORA,
    ResearchMethod.FULL_FINE_TUNE,
    ResearchMethod.DISTILLATION,
}


@dataclass
class FineTuneSpec:
    experiment_id: str
    base_model: str
    dataset_ref: str
    method: ResearchMethod = ResearchMethod.QLORA
    epochs: int = 1
    learning_rate: float = 2e-4
    lora_r: int = 8
    quantization: str = "4bit"
    max_seq_len: int = 512
    hardware: HardwareRequirement = field(default_factory=HardwareRequirement)
    notes: str = ""

    def validate(self) -> None:
        if self.method not in TRAINING_METHODS:
            raise InvalidResearchJob(f"{self.method.value} is not a training method")
        if not self.base_model or not self.dataset_ref:
            raise InvalidResearchJob("base_model and dataset_ref are required")
        if self.epochs < 1 or self.learning_rate <= 0 or self.lora_r < 1:
            raise InvalidResearchJob("training hyperparameters must be positive")
        if self.quantization not in ("4bit", "8bit", "none"):
            raise InvalidResearchJob("quantization must be 4bit, 8bit or none")

    def to_job(self) -> ResearchJob:
        self.validate()
        return ResearchJob(
            experiment_id=self.experiment_id,
            title=f"{self.method.value} of {self.base_model}",
            task_type="training",
            complexity=3,
            method=self.method,
            model=self.base_model,
            dataset_ref=self.dataset_ref,
            hardware=self.hardware,
            outputs=["checkpoint", "evaluation_report"],
            metadata={
                "epochs": self.epochs,
                "learning_rate": self.learning_rate,
                "lora_r": self.lora_r,
                "quantization": self.quantization,
                "max_seq_len": self.max_seq_len,
                "notes": self.notes,
            },
        )


class TrainingService:
    def __init__(self, coordinator: ResearchCoordinator, store: ArtifactStore) -> None:
        self.coordinator = coordinator
        self.store = store

    async def submit(
        self,
        spec: FineTuneSpec,
        adapters: Iterable[ResearchPlatformAdapter],
        credentials: Iterable[CredentialRef] = (),
        private_markers: Iterable[str] = (),
    ) -> tuple[ResearchRun, ResearchJob]:
        job = spec.to_job()
        run = await self.coordinator.submit(
            job,
            adapters,
            credentials=credentials,
            private_markers=private_markers,
        )
        return run, job

    def record_checkpoint(self, run: ResearchRun, checkpoint_ref: str) -> Dict[str, Any]:
        if not checkpoint_ref:
            raise InvalidResearchJob("checkpoint_ref is required")
        record = {
            "experiment_id": run.job.experiment_id,
            "model": run.job.model,
            "method": run.job.method.value,
            "checkpoint_ref": checkpoint_ref,
            "provider": run.provider,
        }
        self.store.put(
            artifact_key(
                run.job.experiment_id, ArtifactKind.CHECKPOINT, "checkpoint.json"
            ),
            json.dumps(record, sort_keys=True, indent=2).encode("utf-8"),
        )
        return record

    @staticmethod
    def validate_improvement(
        baseline_score: float, post_training_score: float, min_delta: float = 0.0
    ) -> None:
        """Independent quality control: successful training is not proof of quality."""
        if post_training_score - baseline_score < min_delta:
            raise NoImprovement(
                f"post-training score {post_training_score} did not exceed "
                f"baseline {baseline_score} by {min_delta}"
            )
