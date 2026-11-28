"""WP0 — research artifact contract and S3-compatible layout (OD-41).

Every experiment gets an immutable ID and a deterministic artifact layout.
Artifacts are written to an IAM-controlled store before a temporary notebook
session can expire. The default local store is for tests/staging; Phase 1
adds the S3 adapter behind the same interface.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Protocol
from uuid import uuid4


class ArtifactKind(str, Enum):
    JOB_SPEC = "job_spec"
    CODE = "code"
    DATASET = "dataset"
    LOG = "log"
    CHECKPOINT = "checkpoint"
    BENCHMARK = "benchmark"
    RESULT = "result"


def new_experiment_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"exp_{stamp}_{uuid4().hex[:12]}"


def artifact_key(experiment_id: str, kind: ArtifactKind, filename: str) -> str:
    safe = Path(filename).name
    return f"experiments/{experiment_id}/{kind.value}/{safe}"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass
class ResearchArtifact:
    experiment_id: str
    kind: ArtifactKind
    relative_path: str
    sha256: str
    size_bytes: int
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data


class ArtifactStore(Protocol):
    def put(self, key: str, payload: bytes, metadata: Optional[Dict] = None) -> ResearchArtifact: ...  # type: ignore[type-arg]

    def get(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...

    def list(self, experiment_id: str) -> List[ResearchArtifact]: ...


class FileSystemArtifactStore:
    """Local implementation used for tests and staging.

    Keys are relative paths under `root`; writing is atomic via a temporary file.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._index: Dict[str, ResearchArtifact] = {}

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError("artifact key escapes the store root")
        return path

    def put(self, key: str, payload: bytes, metadata: Optional[Dict] = None) -> ResearchArtifact:  # type: ignore[type-arg]
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            handle.write(payload)
            tmp = Path(handle.name)
        tmp.replace(path)
        experiment_id = key.split("/")[1] if key.startswith("experiments/") else "unknown"
        try:
            kind = ArtifactKind(key.split("/")[2])
        except (IndexError, ValueError):
            kind = ArtifactKind.RESULT
        artifact = ResearchArtifact(
            experiment_id=experiment_id,
            kind=kind,
            relative_path=key,
            sha256=sha256_bytes(payload),
            size_bytes=len(payload),
            metadata=metadata or {},
        )
        self._index[key] = artifact
        return artifact

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def list(self, experiment_id: str) -> List[ResearchArtifact]:
        return [
            artifact
            for key, artifact in self._index.items()
            if key.startswith(f"experiments/{experiment_id}/")
        ]

    def keys(self, prefix: str = "") -> List[str]:
        """Scan the store on disk so state survives a process restart."""
        base = self.root.resolve()
        return [
            path.relative_to(base).as_posix()
            for path in sorted(base.rglob("*"))
            if path.is_file()
            and (not prefix or path.relative_to(base).as_posix().startswith(prefix))
        ]


def default_store() -> ArtifactStore:
    """Configured artifact store: durable S3/MinIO or local filesystem.

    All research evidence (registry, benchmarks, serving state) must use the
    same store so a signed promotion survives process restarts.
    """
    from app.core.config import settings

    if settings.research_artifact_store.lower() == "s3":
        from .s3_store import S3ArtifactStore

        return S3ArtifactStore(
            bucket=settings.s3_bucket, prefix=settings.research_artifact_prefix
        )
    root = settings.model_release_artifact_root or str(
        Path(tempfile.gettempdir()) / "iam-model-releases"
    )
    return FileSystemArtifactStore(root)


def persist_manifest(store: ArtifactStore, experiment_id: str, manifest: Dict) -> ResearchArtifact:  # type: ignore[type-arg]
    payload = json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8")
    return store.put(
        artifact_key(experiment_id, ArtifactKind.JOB_SPEC, "job.json"),
        payload,
        {"content_type": "application/json"},
    )
