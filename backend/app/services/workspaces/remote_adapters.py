"""Remote workspace provider adapters (WS-05).

Coder and Codespaces are optional, replaceable resources. Every network call
is opt-in and fail-closed: no token, no call; no configured command bridge, no
execution. Tokens are read from the environment only and never logged or stored.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.workspaces.errors import WorkspaceError


class RemoteProviderError(WorkspaceError):
    """Raised when a remote provider is unavailable or refuses an operation."""


class RemoteWorkspaceAdapter(ABC):
    name = "abstract"

    def _ensure_enabled(self) -> None:
        if not settings.workspace_remote_execution_enabled:
            raise RemoteProviderError(
                "remote workspace execution is disabled; local fallback remains available"
            )

    @staticmethod
    def _token(env_var: str) -> str:
        value = os.environ.get(env_var)
        if not value:
            raise RemoteProviderError(
                f"remote provider token environment variable '{env_var}' is not set"
            )
        return value

    async def _request(
        self, method: str, url: str, token: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        self._ensure_enabled()
        try:
            async with httpx.AsyncClient(
                timeout=settings.workspace_remote_timeout_seconds,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                    "User-Agent": "IAM-Workspace-Manager/1.0",
                },
            ) as client:
                response = await client.request(method, url, json=payload)
        except httpx.HTTPError as exc:
            raise RemoteProviderError(
                f"remote provider request failed: {type(exc).__name__}"
            ) from exc
        if response.status_code >= 400:
            # Never echo response bodies: they can contain credentials or PII.
            raise RemoteProviderError(
                f"remote provider returned HTTP {response.status_code}"
            )
        try:
            data = response.json()
        except ValueError:
            data = {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _external_id(data: Dict[str, Any]) -> str:
        value = data.get("id") or data.get("name") or data.get("workspace_id")
        if not value:
            raise RemoteProviderError("remote provider response contained no workspace id")
        return str(value)

    @abstractmethod
    async def provision(self, name: str, actor: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def start(self, external_id: str, actor: str) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def execute(
        self, external_id: str, command: str, env_names: List[str], actor: str
    ) -> Dict[str, Any]:
        ...

    @abstractmethod
    async def destroy(self, external_id: str, actor: str) -> Dict[str, Any]:
        ...

    async def save(self, external_id: str, actor: str) -> Dict[str, Any]:
        """Remote providers persist server-side; only a metadata record is kept."""
        self._ensure_enabled()
        return {"status": "saved", "external_id": external_id, "provider": self.name}

    def _execute_payload(self, command: str, env_names: List[str]) -> Dict[str, Any]:
        return {"command": command, "env": list(env_names)}

    def _outcome(self, data: Dict[str, Any], command: str) -> Dict[str, Any]:
        status = str(data.get("status") or "completed").lower()
        return {
            "status": "completed" if status in ("completed", "success", "ok", "succeeded") else "failed",
            "dry_run": False,
            "simulated": False,
            "adapter": self.name,
            "command": command,
            "stdout": str(data.get("stdout") or "")[:2000],
            "stderr": str(data.get("stderr") or "")[:2000],
        }


class CoderWorkspaceAdapter(RemoteWorkspaceAdapter):
    name = "coder"

    def _url(self, path: str, external_id: str = "") -> str:
        base = settings.workspace_coder_url.rstrip("/")
        if not base:
            raise RemoteProviderError("WORKSPACE_CODER_URL is not configured")
        return base + path.format(id=external_id)

    async def provision(self, name: str, actor: str) -> Dict[str, Any]:
        token = self._token(settings.workspace_coder_token_env)
        if not settings.workspace_coder_template_id:
            raise RemoteProviderError("WORKSPACE_CODER_TEMPLATE_ID is not configured")
        data = await self._request(
            "POST",
            self._url(settings.workspace_coder_create_path),
            token,
            {"name": name, "template_id": settings.workspace_coder_template_id},
        )
        return {"external_id": self._external_id(data), "provider": self.name}

    async def start(self, external_id: str, actor: str) -> Dict[str, Any]:
        token = self._token(settings.workspace_coder_token_env)
        await self._request("POST", self._url(settings.workspace_coder_start_path, external_id), token)
        return {"status": "active", "external_id": external_id}

    async def execute(self, external_id: Any, command: Any, env_names: Any, actor: Any) -> Any:
        if not settings.workspace_coder_execute_path:
            raise RemoteProviderError(
                "WORKSPACE_CODER_EXECUTE_PATH is not configured; command execution is unavailable"
            )
        token = self._token(settings.workspace_coder_token_env)
        data = await self._request(
            "POST",
            self._url(settings.workspace_coder_execute_path, external_id),
            token,
            self._execute_payload(command, env_names),
        )
        return self._outcome(data, command)

    async def destroy(self, external_id: Any, actor: Any) -> Any:
        token = self._token(settings.workspace_coder_token_env)
        await self._request("DELETE", self._url(settings.workspace_coder_destroy_path, external_id), token)
        return {"status": "destroyed", "external_id": external_id}


class CodespacesWorkspaceAdapter(RemoteWorkspaceAdapter):
    name = "codespaces"

    def _repo(self) -> str:
        if not settings.workspace_codespaces_repo:
            raise RemoteProviderError("WORKSPACE_CODESPACES_REPO is not configured")
        return settings.workspace_codespaces_repo.strip("/")

    def _url(self, path: str, external_id: str = "") -> str:
        base = settings.workspace_codespaces_api_base.rstrip("/")
        return base + path.format(repo=self._repo(), id=external_id)

    async def provision(self, name: Any, actor: Any) -> Any:
        token = self._token(settings.workspace_codespaces_token_env)
        data = await self._request(
            "POST",
            self._url(settings.workspace_codespaces_create_path),
            token,
            {"ref": settings.workspace_codespaces_ref},
        )
        return {"external_id": self._external_id(data), "provider": self.name}

    async def start(self, external_id: Any, actor: Any) -> Any:
        token = self._token(settings.workspace_codespaces_token_env)
        await self._request(
            "POST", self._url(settings.workspace_codespaces_start_path, external_id), token
        )
        return {"status": "active", "external_id": external_id}

    async def execute(self, external_id: Any, command: Any, env_names: Any, actor: Any) -> Any:
        if not settings.workspace_codespaces_execute_path:
            raise RemoteProviderError(
                "WORKSPACE_CODESPACES_EXECUTE_PATH is not configured; "
                "command execution is unavailable"
            )
        token = self._token(settings.workspace_codespaces_token_env)
        data = await self._request(
            "POST",
            self._url(settings.workspace_codespaces_execute_path, external_id),
            token,
            self._execute_payload(command, env_names),
        )
        return self._outcome(data, command)

    async def destroy(self, external_id: Any, actor: Any) -> Any:
        token = self._token(settings.workspace_codespaces_token_env)
        await self._request(
            "DELETE", self._url(settings.workspace_codespaces_destroy_path, external_id), token
        )
        return {"status": "destroyed", "external_id": external_id}


def remote_adapter_for(provider: str) -> RemoteWorkspaceAdapter:
    if provider == "coder":
        return CoderWorkspaceAdapter()
    if provider == "codespaces":
        return CodespacesWorkspaceAdapter()
    raise RemoteProviderError(f"no remote adapter for provider: {provider}")
