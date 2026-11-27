"""WP14 — model registry, approval gates and rollback (OD-41).

No model becomes deployable without benchmark evidence and a capability profile.
Protected-core changes require a signed Creator approval (OD-03/OD-11/OD-19).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, fields, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from .artifacts import ArtifactKind, ArtifactStore, artifact_key
from .base import CreatorApprovalRequired, ResearchError
from .governance import ActionKind, AutonomyGate, SignedApproval


class ModelNotApproved(ResearchError):
    """The version has not passed approval before deployment."""


@dataclass
class ModelVersion:
    model: str
    version: str
    checkpoint_ref: str
    benchmark_score: float
    capability_profile: Dict[str, Any] = field(default_factory=dict)
    status: str = "candidate"  # candidate | approved | deployed | rolled_back
    approval: Optional[SignedApproval] = None
    rollback_ref: Optional[str] = None
    benchmark_ref: str = ""
    baseline_score: float = 0.0
    min_improvement: float = 0.0
    dataset_ref: str = ""
    dataset_sha256: str = ""
    licence: str = ""
    consent_recorded: bool = False
    poisoning_scan_ref: str = ""
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data


class ModelRegistry:
    def __init__(
        self,
        store: ArtifactStore,
        gate: Optional[AutonomyGate] = None,
        audit_sink: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ) -> None:
        self.store = store
        self.gate = gate or AutonomyGate(audit_sink=audit_sink)
        self.audit_sink = audit_sink
        self._versions: Dict[str, ModelVersion] = {}
        self._active: Dict[str, str] = {}

    def hydrate(self) -> int:
        """Reload persisted versions after restart (fail-closed on bad data)."""
        keys = getattr(self.store, "keys", None)
        if not callable(keys):
            return 0
        loaded = 0
        allowed = {item.name for item in fields(ModelVersion)}
        for key in keys("experiments/"):
            if not key.endswith("/result/model_version.json"):
                continue
            try:
                data = json.loads(self.store.get(key).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(data, dict) or not data.get("model") or not data.get("version"):
                continue
            approval = data.get("approval")
            if isinstance(approval, dict):
                data["approval"] = SignedApproval(
                    request_id=str(approval.get("request_id", "")),
                    signed_by=str(approval.get("signed_by", "")),
                    signature=str(approval.get("signature", "")),
                )
            version = ModelVersion(**{k: v for k, v in data.items() if k in allowed})
            identifier = f"{version.model}@{version.version}"
            self._versions[identifier] = version
            if version.status == "deployed":
                self._active[version.model] = version.version
            loaded += 1
        return loaded

    def get(self, model: str, version: str) -> ModelVersion:
        key = f"{model}@{version}"
        if key not in self._versions:
            self.hydrate()
        if key not in self._versions:
            raise ResearchError(f"unknown model version: {key}")
        return self._versions[key]

    @staticmethod
    def _key(version: ModelVersion) -> str:
        safe_model = re.sub(r"[^A-Za-z0-9_.-]", "_", version.model)
        safe_version = re.sub(r"[^A-Za-z0-9_.-]", "_", version.version)
        experiment_id = f"registry_{safe_model}_{safe_version}"
        return artifact_key(
            experiment_id, ArtifactKind.RESULT, "model_version.json"
        )

    def _persist(self, version: ModelVersion) -> None:
        key = self._key(version)
        self.store.put(
            key,
            json.dumps(version.to_dict(), sort_keys=True, indent=2).encode("utf-8"),
        )
        self._versions[f"{version.model}@{version.version}"] = version

    def _audit(self, event: str, details: Dict[str, Any]) -> None:
        if self.audit_sink:
            self.audit_sink(event, details)

    def register(self, version: ModelVersion) -> ModelVersion:
        if not version.checkpoint_ref or not version.capability_profile:
            raise ResearchError(
                "a version needs a checkpoint and a measured capability profile"
            )
        if version.status != "candidate":
            raise ResearchError("new versions must be registered as candidates")
        self._persist(version)
        self._audit("model_version_registered", {
            "model": version.model, "version": version.version
        })
        return version

    def approve(
        self,
        model: str,
        version: str,
        approval: Optional[SignedApproval] = None,
        protected: bool = False,
    ) -> ModelVersion:
        key = f"{model}@{version}"
        entry = self._versions[key]
        if protected:
            self.gate.assert_allowed(ActionKind.PROTECTED_CORE, approval)
        elif approval is not None:
            self.gate.assert_allowed(ActionKind.ROUTINE, approval)
        entry.status = "approved"
        entry.approval = approval
        self._persist(entry)
        self._audit("model_version_approved", {
            "model": model, "version": version, "protected": protected
        })
        return entry

    def deploy(self, model: str, version: str) -> ModelVersion:
        entry = self._versions[f"{model}@{version}"]
        if entry.status != "approved":
            raise ModelNotApproved(f"{model}@{version} is not approved for deployment")
        entry.status = "deployed"
        self._persist(entry)
        self._active[model] = version
        self._audit("model_version_deployed", {"model": model, "version": version})
        return entry

    def rollback(self, model: str, target_version: str) -> ModelVersion:
        if model not in self._active:
            raise ResearchError(f"{model} has no deployed version to roll back from")
        key = f"{model}@{target_version}"
        if key not in self._versions:
            self.hydrate()
        if key not in self._versions:
            raise ResearchError(f"unknown rollback target: {key}")
        target = self._versions[key]
        previous = self._active[model]
        target.rollback_ref = previous
        # Only the rollback target may remain "deployed". hydrate() rebuilds
        # active state from that status, so leaving the old version deployed
        # would silently reactivate it after a process restart.
        for version in self.list_versions(model):
            if version is target or version.status != "deployed":
                continue
            version.status = "rolled_back"
            self._persist(version)
        target.status = "deployed"
        self._persist(target)
        self._active[model] = target_version
        self._audit("model_rollback", {
            "model": model, "from": previous, "to": target_version
        })
        return target

    def active(self, model: str) -> Optional[str]:
        return self._active.get(model)

    def list_versions(self, model: str) -> List[ModelVersion]:
        return [
            version
            for key, version in self._versions.items()
            if key.startswith(f"{model}@")
        ]
