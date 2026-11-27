"""WP3 — common training/research job format (OD-41).

One job spec is submitted unchanged to any platform adapter. Hardware needs
are explicit so the quota guard (WP2) can refuse jobs a platform cannot serve.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

from .artifacts import new_experiment_id
from .base import InvalidResearchJob


class ResearchMethod(str, Enum):
    SFT = "sft"
    LORA = "lora"
    QLORA = "qlora"
    FULL_FINE_TUNE = "full_fine_tune"
    DISTILLATION = "distillation"
    EVALUATION = "evaluation"
    SERVING = "serving"


@dataclass
class HardwareRequirement:
    min_ram_mb: int = 4096
    min_vram_mb: int = 0
    min_gpu_capability: float = 0.0  # vLLM needs >= 7.5
    max_runtime_minutes: int = 60
    gpu_required: bool = False


@dataclass
class ResearchJob:
    experiment_id: str
    title: str
    task_type: str
    complexity: int  # 1 simple ... 5 hosted specialist
    method: ResearchMethod
    model: str
    dataset_ref: str = ""
    hardware: HardwareRequirement = field(default_factory=HardwareRequirement)
    dependencies: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_manifest(self) -> Dict[str, Any]:
        data = asdict(self)
        data["method"] = self.method.value
        return data

    @classmethod
    def from_manifest(cls, manifest: Dict[str, Any]) -> "ResearchJob":
        data = dict(manifest)
        method = ResearchMethod(data.pop("method"))
        data["hardware"] = HardwareRequirement(**data.get("hardware", {}))
        return cls(method=method, **data)


def validate_job(job: ResearchJob) -> None:
    """Fail closed on malformed or unsafe job specs."""
    if not job.experiment_id or not job.title or not job.model:
        raise InvalidResearchJob("experiment_id, title and model are required")
    if not 1 <= job.complexity <= 5:
        raise InvalidResearchJob("complexity must be between 1 and 5")
    if job.hardware.min_ram_mb <= 0 or job.hardware.max_runtime_minutes <= 0:
        raise InvalidResearchJob("hardware requirements must be positive")
    if job.method == ResearchMethod.SERVING and job.hardware.min_gpu_capability < 7.5:
        raise InvalidResearchJob("serving jobs require min_gpu_capability >= 7.5")
    if job.hardware.gpu_required and job.hardware.min_vram_mb <= 0:
        raise InvalidResearchJob("gpu_required jobs must declare min_vram_mb")
    if job.method in (
        ResearchMethod.SFT,
        ResearchMethod.LORA,
        ResearchMethod.QLORA,
        ResearchMethod.FULL_FINE_TUNE,
        ResearchMethod.DISTILLATION,
    ) and not job.dataset_ref:
        raise InvalidResearchJob("training jobs must declare a dataset_ref")
    for key in ("api_key", "token", "password", "secret", "credential"):
        if key in str(job.metadata).lower():
            raise InvalidResearchJob("job metadata must not contain secrets")


def new_job(**kwargs: Any) -> ResearchJob:
    """Create a job with a fresh immutable experiment ID."""
    job = ResearchJob(experiment_id=new_experiment_id(), **kwargs)
    validate_job(job)
    return job
