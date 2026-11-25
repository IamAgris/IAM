"""OEDIE Free Infrastructure Provider Adapter layer (IAM Document 22).

Default-disabled. External free platforms are supplementary capacity only;
IAM remains fully operational when all of them are unavailable.
"""

from .base import (
    CredentialMissing,
    EnvironmentState,
    FreeTierUnverified,
    ProviderInfo,
    ProviderUnavailable,
    QuotaExceeded,
    QuotaSnapshot,
    SandboxCapability,
    SandboxEnvironment,
    SandboxError,
    WorkloadRequest,
)
from .quota import DEFAULT_SAFETY_MARGIN, QuotaGuard
from .manager import FreeSandboxManager, build_default_manager

__all__ = [
    "CredentialMissing",
    "DEFAULT_SAFETY_MARGIN",
    "EnvironmentState",
    "FreeSandboxManager",
    "FreeTierUnverified",
    "ProviderInfo",
    "ProviderUnavailable",
    "QuotaExceeded",
    "QuotaGuard",
    "QuotaSnapshot",
    "SandboxCapability",
    "SandboxEnvironment",
    "SandboxError",
    "WorkloadRequest",
    "build_default_manager",
]
