"""Common contract for free infrastructure provider adapters (Doc 22, OD-15/OD-35).

Every adapter is a *candidate* provider. It never holds protected-core data,
signing material or private memories, and it must refuse to act unless its
free-tier state is verified and within the quota safety margin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Set


class SandboxCapability(str, Enum):
    DEVELOPMENT = "development"
    NOTEBOOK = "notebook"
    MODEL_EVALUATION = "model_evaluation"
    INFERENCE = "inference"
    WEB_PROTOTYPE = "web_prototype"


class EnvironmentState(str, Enum):
    DISCOVERED = "discovered"
    REGISTERED = "registered"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class SandboxError(RuntimeError):
    """Base error for sandbox operations."""


class SandboxDisabled(SandboxError):
    """The capability is not activated; no external action is permitted."""


class CredentialMissing(SandboxError):
    """Provider credentials are not configured."""


class FreeTierUnverified(SandboxError):
    """Free-tier state has not been verified against a current official source."""


class QuotaExceeded(SandboxError):
    """Free allowance is exhausted or within the safety margin."""


class ProviderUnavailable(SandboxError):
    """No eligible free provider can serve the workload."""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class QuotaSnapshot:
    provider: str
    used_percent: Optional[float] = None
    unit: str = ""
    remaining: Optional[float] = None
    resets_at: Optional[str] = None
    verified_at: Optional[str] = None
    source_url: Optional[str] = None
    reason: Optional[str] = None

    @property
    def verified(self) -> bool:
        return (
            self.used_percent is not None
            and self.verified_at is not None
            and bool(self.source_url)
        )


@dataclass
class WorkloadRequest:
    task_id: str
    capability: SandboxCapability
    description: str
    artifact_refs: List[str] = field(default_factory=list)
    max_runtime_seconds: int = 1800
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SandboxEnvironment:
    provider: str
    external_id: str
    capability: SandboxCapability
    state: EnvironmentState
    created_at: str = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderInfo:
    name: str
    capabilities: Set[SandboxCapability]
    terms_url: str
    headless: bool = True
    notes: str = ""


class ProviderAdapter(Protocol):
    """Contract implemented by every free infrastructure provider adapter."""

    info: ProviderInfo

    def credentials_available(self) -> bool: ...

    async def verify_free_tier(self) -> QuotaSnapshot: ...

    async def provision(self, request: WorkloadRequest) -> SandboxEnvironment: ...

    async def start(self, external_id: str) -> None: ...

    async def stop(self, external_id: str) -> None: ...

    async def delete(self, external_id: str) -> None: ...

    async def status(self, external_id: str) -> SandboxEnvironment: ...

    async def collect_results(self, external_id: str) -> Dict[str, Any]: ...
