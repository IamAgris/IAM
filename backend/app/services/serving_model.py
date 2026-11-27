"""Active serving model for IAM (OD-38 / OD-40).

IAM's identity, memory and governance are model-independent. The model that
actually answers requests is a replaceable capability tracked here:

  * default  -> ``settings.iam_primary_model`` (the approved local primary);
  * override -> a version promoted through the signed release gate;
  * rollback -> the model that was serving before that promotion.

The state lives in the artifact store, never in model weights, private memory
or the protected constitution. This is the bridge between IAM's self-improvement
cycle and live inference: a promoted model does not become the primary brain
until it has passed benchmark, provenance and signed-authority gates.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.ai_research.artifacts import FileSystemArtifactStore

SERVING_KEY = "serving/primary.json"
CONFIG_SOURCE = "config"
RELEASE_SOURCE = "release"
ROLLBACK_SOURCE = "rollback"


def _store() -> FileSystemArtifactStore:
    root = settings.model_release_artifact_root or str(
        Path(tempfile.gettempdir()) / "iam-model-releases"
    )
    return FileSystemArtifactStore(root)


@dataclass(frozen=True)
class ServingModel:
    model: str
    source: str = CONFIG_SOURCE
    version: Optional[str] = None
    previous: Optional[str] = None
    previous_version: Optional[str] = None
    activated_at: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _configured() -> ServingModel:
    return ServingModel(model=settings.iam_primary_model)


def current() -> ServingModel:
    """Return the active serving model, falling back to the configured primary."""
    store = _store()
    if not store.exists(SERVING_KEY):
        return _configured()
    try:
        payload = json.loads(store.get(SERVING_KEY).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, OSError):
        return _configured()
    if not isinstance(payload, dict):
        return _configured()
    model = str(payload.get("model") or "").strip()
    if not model:
        return _configured()
    allowed = set(ServingModel.__dataclass_fields__)
    values = {key: value for key, value in payload.items() if key in allowed}
    values["model"] = model
    return ServingModel(**values)


def _write(entry: ServingModel, actor: str = "") -> ServingModel:
    _store().put(
        SERVING_KEY,
        json.dumps(entry.as_dict(), sort_keys=True, indent=2).encode("utf-8"),
        {"content_type": "application/json", "actor": actor},
    )
    return entry


def activate(
    model: str,
    *,
    version: Optional[str] = None,
    source: str = RELEASE_SOURCE,
    actor: str = "",
) -> ServingModel:
    """Activate a promoted model, remembering what it replaced."""
    model = str(model or "").strip()
    if not model:
        raise ValueError("model is required")
    prior = current()
    entry = ServingModel(
        model=model,
        source=source,
        version=version,
        previous=prior.model,
        previous_version=prior.version,
        activated_at=datetime.now(timezone.utc).isoformat(),
    )
    return _write(entry, actor)


def rollback(target_version: Optional[str] = None) -> ServingModel:
    """Restore the model that was serving before the active override.

    ``previous`` is cleared on purpose: a second rollback must not toggle back
    to the model that was just rolled back from. When the caller names a target,
    it must match the recorded previous version.
    """
    prior = current()
    if target_version and prior.version == target_version:
        return prior  # already serving the requested target
    if not prior.previous:
        return _write(_configured())
    if target_version and target_version != prior.previous_version:
        raise ValueError(
            f"rollback target {target_version} does not match the served previous version"
        )
    entry = ServingModel(
        model=prior.previous,
        source=ROLLBACK_SOURCE,
        version=prior.previous_version,
        previous=None,
        previous_version=None,
        activated_at=datetime.now(timezone.utc).isoformat(),
    )
    return _write(entry)
