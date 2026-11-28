"""WP15 — research memory and continuous improvement (OD-41).

Failed experiments are retained and become explicit inputs to the next plan;
successes are not assumed to generalise.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .artifacts import ArtifactKind, ArtifactStore, artifact_key
from .base import ResearchError


@dataclass
class ExperimentRecord:
    experiment_id: str
    task_type: str
    method: str
    score: float
    succeeded: bool
    diagnosis: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class ResearchMemory:
    def __init__(self, store: ArtifactStore) -> None:
        self.store = store
        self._records: Dict[str, ExperimentRecord] = {}

    def hydrate(self) -> int:
        """Restore retained experiments from the artifact store after restart."""
        keys = getattr(self.store, "keys", None)
        if not callable(keys):
            return 0
        loaded = 0
        for key in keys("experiments/"):
            if not key.endswith("_memory.json"):
                continue
            try:
                payload = json.loads(self.store.get(key).decode("utf-8"))
            except (ValueError, UnicodeDecodeError, OSError):
                continue
            if not isinstance(payload, dict) or not payload.get("experiment_id"):
                continue
            self._records[payload["experiment_id"]] = ExperimentRecord(
                experiment_id=str(payload["experiment_id"]),
                task_type=str(payload.get("task_type", "")),
                method=str(payload.get("method", "")),
                score=float(payload.get("score", 0) or 0),
                succeeded=bool(payload.get("succeeded", False)),
                diagnosis=str(payload.get("diagnosis", "")),
                tags=list(payload.get("tags", [])),
                created_at=str(payload.get("created_at", "")),
            )
            loaded += 1
        return loaded

    def record(self, entry: ExperimentRecord) -> ExperimentRecord:
        if not entry.experiment_id:
            raise ResearchError("experiment_id is required")
        self._records[entry.experiment_id] = entry
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", entry.experiment_id)
        self.store.put(
            artifact_key(entry.experiment_id, ArtifactKind.RESULT, f"{safe}_memory.json"),
            json.dumps(entry.to_dict(), sort_keys=True, indent=2).encode("utf-8"),
        )
        return entry

    def failures(self, task_type: Optional[str] = None) -> List[ExperimentRecord]:
        return [
            record
            for record in self._records.values()
            if not record.succeeded and (task_type is None or record.task_type == task_type)
        ]

    def successes(self, task_type: Optional[str] = None) -> List[ExperimentRecord]:
        return [
            record
            for record in self._records.values()
            if record.succeeded and (task_type is None or record.task_type == task_type)
        ]

    def suggest_next(self, task_type: str) -> Dict[str, object]:
        """Turn retained failures into concrete inputs for the next experiment."""
        failures = self.failures(task_type)
        successes = self.successes(task_type)
        avoid = sorted({tag for failure in failures for tag in failure.tags})
        strongest = max(successes, key=lambda r: r.score) if successes else None
        return {
            "task_type": task_type,
            "from_failures": [record.experiment_id for record in failures],
            "diagnoses": [record.diagnosis for record in failures if record.diagnosis],
            "avoid": avoid,
            "reuse": strongest.method if strongest else None,
            "rationale": (
                "Prior experiments with these configurations failed; reuse the "
                "best measured method and avoid the tagged failure modes."
            ),
        }
