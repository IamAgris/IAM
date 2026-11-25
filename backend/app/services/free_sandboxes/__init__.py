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
    SandboxDisabled,
    WorkloadRequest,
)
from .quota import DEFAULT_SAFETY_MARGIN, QuotaGuard
from .manager import FreeSandboxManager, SchedulerPolicy, build_default_manager
from .discovery import ProviderDiscovery, DiscoverySeed, DiscoveredProvider
from .registration import RegistrationDecision, RegistrationGate
from .results import redact, wrap_untrusted
from .service import FreeSandboxService
from .monitor import FreeSandboxMonitor
from .browser import PlaywrightBrowserOpener

__all__ = [
    "CredentialMissing",
    "DEFAULT_SAFETY_MARGIN",
    "EnvironmentState",
    "DiscoveredProvider",
    "DiscoverySeed",
    "FreeSandboxManager",
    "FreeSandboxService",
    "FreeSandboxMonitor",
    "PlaywrightBrowserOpener",
    "ProviderDiscovery",
    "RegistrationDecision",
    "RegistrationGate",
    "SchedulerPolicy",
    "redact",
    "wrap_untrusted",
    "FreeTierUnverified",
    "ProviderInfo",
    "ProviderUnavailable",
    "QuotaExceeded",
    "QuotaGuard",
    "QuotaSnapshot",
    "SandboxCapability",
    "SandboxEnvironment",
    "SandboxError",
    "SandboxDisabled",
    "WorkloadRequest",
    "build_default_manager",
]
