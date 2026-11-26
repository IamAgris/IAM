"""WS-05/WS-06 provider replacement and continuity.

Online coding platforms are optional, interchangeable resources. Availability
is determined only from configuration and the *presence* of an environment
variable — secret values are never read into logs, models or the database.
The local/self-hosted provider is always the final fallback.
"""

import os
from dataclasses import dataclass
from typing import List, Optional

from app.core.config import settings
from app.services.workspaces.errors import WorkspaceError


@dataclass(frozen=True)
class ProviderStatus:
    name: str
    available: bool
    reason: str

    def as_dict(self):
        return {"name": self.name, "available": self.available, "reason": self.reason}


def _token_present(env_var: str) -> bool:
    return bool(env_var and os.environ.get(env_var))


def provider_statuses() -> List[ProviderStatus]:
    configured = [
        item.strip()
        for item in settings.workspace_providers.split(",")
        if item.strip()
    ]
    statuses: List[ProviderStatus] = []
    for name in configured:
        if name == "local":
            statuses.append(ProviderStatus(name, True, "self-hosted fallback always available"))
        elif name == "coder":
            ready = (
                settings.workspace_remote_execution_enabled
                and bool(settings.workspace_coder_url)
                and _token_present(settings.workspace_coder_token_env)
            )
            statuses.append(
                ProviderStatus(
                    name,
                    ready,
                    "requires remote execution enabled, WORKSPACE_CODER_URL and its token"
                    if not ready
                    else "configured",
                )
            )
        elif name == "codespaces":
            ready = (
                settings.workspace_remote_execution_enabled
                and bool(settings.workspace_codespaces_repo)
                and _token_present(settings.workspace_codespaces_token_env)
            )
            statuses.append(
                ProviderStatus(
                    name,
                    ready,
                    "requires remote execution enabled, WORKSPACE_CODESPACES_REPO and its token"
                    if not ready
                    else "configured",
                )
            )
        else:
            statuses.append(ProviderStatus(name, False, "unknown provider"))
    if not any(status.name == "local" for status in statuses):
        statuses.append(ProviderStatus("local", True, "self-hosted fallback always available"))
    return statuses


def select_provider(preferred: Optional[str] = None) -> str:
    """Pick the preferred provider, then another ready one, then local."""
    statuses = provider_statuses()
    if preferred:
        for status in statuses:
            if status.name == preferred and status.available:
                return preferred
    for status in statuses:
        if status.available and status.name != "local":
            return status.name
    return "local"


def assert_provider_available(provider: str) -> ProviderStatus:
    for status in provider_statuses():
        if status.name == provider:
            if not status.available:
                raise WorkspaceError(f"provider '{provider}' is unavailable: {status.reason}")
            return status
    raise WorkspaceError(f"unsupported workspace provider: {provider}")
