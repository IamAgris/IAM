"""WS-01/WS-02 workspace manager — isolated, replaceable dev environments.

Workspaces are created through a controlled API (not by clicking in a browser).
The default adapter is a non-executing stub. The Docker adapter keeps the same
hardening as Skill Runtime: no protected-core mount, no default network,
non-root user, dropped capabilities and bounded resources. Credentials are
stored by environment-variable *name* only, never by value.
"""

import asyncio
import hashlib
import re
import shutil
import subprocess
import tempfile
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.security import AuditEvent
from app.models.workspace_credentials import WorkspaceCredential
from app.models.workspaces import WorkspaceEnvironment
from app.services.security_policy import forbidden_capability
from app.services.workspaces.errors import WorkspaceError
from app.services.workspaces.providers import (
    assert_provider_available,
    provider_statuses,
    select_provider,
)
from app.services.workspaces.remote_adapters import remote_adapter_for

SUPPORTED_PROVIDERS = ("local", "codespaces", "coder")
CREDENTIAL_PURPOSES = ("git", "package_registry", "api", "test_fixture")
_URL_HOST_PATTERN = re.compile(r"https?://([A-Za-z0-9.-]+)")
STATUS_TRANSITIONS = {
    "provisioning": ("active", "failed"),
    "active": ("saved", "destroyed", "failed"),
    "saved": ("active", "destroyed"),
    "destroyed": (),
    "failed": ("destroyed",),
}
_FORBIDDEN_CREDENTIAL_PREFIXES = (
    "IAM_",
    "CREATOR_",
    "POSTGRES_",
    "DATABASE_",
    "ENCRYPTION_",
    "S3_",
    "REDIS_",
    "LITELLM_",
    "SESSION_",
    "APP_",
)
_ENV_VAR_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{1,63}")
_DENIED_COMMAND_PATTERNS = (
    re.compile(r"(?i)\bsudo\b"),
    re.compile(r"(?i)\bdocker\b"),
    re.compile(r"(?i)chmod\s+777"),
    re.compile(r"(?i)chown\s+root"),
    re.compile(r"(?i)rm\s+-rf\s+/(?:\s|$)"),
)


@dataclass(frozen=True)
class WorkspaceIsolation:
    core_access: bool = False
    network: str = "none"
    read_only_protected: bool = True
    non_root: bool = True
    no_new_privileges: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


DEFAULT_ISOLATION = WorkspaceIsolation()


def validate_isolation(isolation: Dict[str, Any]) -> None:
    """WS-02: no workspace may reach the protected core or an open network."""
    if isolation.get("core_access"):
        raise WorkspaceError("workspaces must never receive protected-core access")
    if isolation.get("network", "none") != "none":
        raise WorkspaceError("workspace network access is not enabled")
    if not isolation.get("read_only_protected", True):
        raise WorkspaceError("protected-core mounts must remain read-only")
    if not isolation.get("non_root", True) or not isolation.get("no_new_privileges", True):
        raise WorkspaceError("workspace execution must be non-root with no new privileges")


def validate_command(command: str) -> str:
    if not command or not isinstance(command, str):
        raise WorkspaceError("command is required")
    if len(command) > 8192:
        raise WorkspaceError("command is too large")
    capability = forbidden_capability(command)
    if capability:
        raise WorkspaceError(f"command requests a prohibited capability: {capability}")
    for pattern in _DENIED_COMMAND_PATTERNS:
        if pattern.search(command):
            raise WorkspaceError("command is not permitted in an isolated workspace")
    return command


def validate_credential_env_var(name: Optional[str]) -> Optional[str]:
    """Accept only a non-sensitive environment-variable *name*."""
    if not name:
        return None
    if not _ENV_VAR_PATTERN.fullmatch(name) or name.startswith(_FORBIDDEN_CREDENTIAL_PREFIXES):
        raise WorkspaceError("credential_env_var must be a non-sensitive variable name")
    return name


def validate_credential_scopes(scopes: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Credential scopes are host allow-lists, never wildcard grants."""
    if scopes is None:
        return {}
    if not isinstance(scopes, dict):
        raise WorkspaceError("scopes must be an object")
    hosts = scopes.get("allowed_hosts", [])
    if not isinstance(hosts, list) or any(
        not isinstance(host, str) or "*" in host for host in hosts
    ):
        raise WorkspaceError("allowed_hosts must be a list of concrete host names")
    return {"allowed_hosts": [host.strip().lower() for host in hosts if host.strip()]}


def credential_env_names(value: Any) -> List[str]:
    """Normalise the single legacy name or the new list of scoped names."""
    if value is None:
        return []
    names = [value] if isinstance(value, str) else list(value)
    for name in names:
        validate_credential_env_var(name)
    return names


def check_command_hosts(command: str, credentials: List[WorkspaceCredential]) -> None:
    """A command may contact a host only via a scoped credential for that host."""
    hosts = {match.lower() for match in _URL_HOST_PATTERN.findall(command)}
    if not hosts:
        return
    permitted = {
        host
        for credential in credentials
        for host in dict(credential.scopes or {}).get("allowed_hosts", [])
    }
    unauthorised = hosts - permitted
    if unauthorised:
        raise WorkspaceError(
            "no scoped workspace credential permits host(s): "
            + ", ".join(sorted(unauthorised))
        )


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def workspace_log_chunks(stream: str, content: str) -> List[Dict[str, Any]]:
    size = max(1, settings.skill_runtime_audit_log_chunk_chars)
    return [
        {"stream": stream, "sequence": index, "content": content[start : start + size]}
        for index, start in enumerate(range(0, len(content), size))
    ]


def workspace_digest(path: Path, *, max_files: int = 200, max_bytes: int = 10_000_000) -> str:
    """Content digest of a saved workspace, bounded for untrusted directories."""
    digest = hashlib.sha256()
    total = 0
    files = sorted(
        (item for item in path.rglob("*") if item.is_file()), key=lambda item: str(item)
    )[:max_files]
    for item in files:
        digest.update(str(item.relative_to(path)).encode("utf-8", "replace"))
        data = item.read_bytes()[:max_bytes]
        total += len(data)
        if total > max_bytes:
            break
        digest.update(data)
    return digest.hexdigest()


class WorkspaceAdapter(ABC):
    name = "abstract"

    @abstractmethod
    async def run(
        self,
        workspace_dir: Path,
        command: str,
        isolation: Dict[str, Any],
        credential_env_vars: List[str],
    ) -> Dict[str, Any]:
        ...


class StubWorkspaceAdapter(WorkspaceAdapter):
    """Default: simulates execution and performs no external work."""

    name = "stub"

    async def run(self, workspace_dir, command, isolation, credential_env_vars):  # type: ignore[no-untyped-def]
        validate_isolation(isolation)
        validate_command(command)
        credential_env_names(credential_env_vars)
        return {
            "status": "completed",
            "dry_run": True,
            "simulated": True,
            "adapter": self.name,
            "command": command,
            "stdout": "simulated execution\n",
            "stderr": "",
        }


class DockerWorkspaceAdapter(WorkspaceAdapter):
    """Runs one bounded command in a disposable, network-less container."""

    name = "docker"

    def command(
        self,
        workspace_dir: Path,
        command: str,
        isolation: Dict[str, Any],
        credential_env_vars: List[str],
    ) -> List[str]:
        validate_isolation(isolation)
        validate_command(command)
        names = credential_env_names(credential_env_vars)
        env_args: List[str] = []
        for name in names:
            env_args.extend(["-e", name])
        return [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--user",
            "65534:65534",
            "--security-opt",
            "no-new-privileges",
            "--cap-drop",
            "ALL",
            "--pids-limit",
            "64",
            "--memory",
            settings.workspace_memory,
            "--cpus",
            str(settings.workspace_cpus),
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            *env_args,
            "-v",
            f"{workspace_dir.resolve()}:/workspace:rw",
            settings.workspace_image,
            "/bin/sh",
            "-c",
            command,
        ]

    async def run(self, workspace_dir, command, isolation, credential_env_vars):  # type: ignore[no-untyped-def]
        docker_command = self.command(
            workspace_dir, command, isolation, credential_env_vars
        )
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                docker_command,
                capture_output=True,
                text=True,
                timeout=settings.workspace_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise WorkspaceError("workspace command timed out") from exc
        except OSError as exc:
            raise WorkspaceError(f"docker unavailable: {type(exc).__name__}") from exc
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "dry_run": False,
            "simulated": False,
            "adapter": self.name,
            "exit_code": result.returncode,
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


def adapter_for(name: str) -> WorkspaceAdapter:
    if name == "stub":
        return StubWorkspaceAdapter()
    if name == "docker":
        return DockerWorkspaceAdapter()
    raise WorkspaceError(f"unknown workspace adapter: {name}")


class WorkspaceService:
    def __init__(
        self,
        db: AsyncSession,
        adapter: Optional[WorkspaceAdapter] = None,
        root: Optional[Path] = None,
    ):
        self.db = db
        self.adapter = adapter or adapter_for(settings.workspace_adapter)
        self.root = Path(root or settings.workspace_root or Path(tempfile.gettempdir()) / "iam-workspaces")

    async def _workspace(self, workspace_id: str) -> WorkspaceEnvironment:
        try:
            identifier = UUID(str(workspace_id))
        except (ValueError, TypeError) as exc:
            raise LookupError("workspace not found") from exc
        result = await self.db.execute(
            select(WorkspaceEnvironment).where(WorkspaceEnvironment.id == identifier)
        )
        workspace = result.scalar_one_or_none()
        if not workspace:
            raise LookupError("workspace not found")
        return workspace

    @staticmethod
    def _remote(workspace: WorkspaceEnvironment):  # type: ignore[no-untyped-def]
        external_id = dict(workspace.isolation or {}).get("provider_external_id")
        if not external_id:
            raise WorkspaceError("remote workspace has no provider external id")
        return remote_adapter_for(workspace.provider), external_id  # type: ignore[arg-type]

    def _directory(self, workspace_id: str, name: str) -> Path:
        slug = re.sub(r"[^a-z0-9-]", "-", name.lower())[:40].strip("-") or "workspace"
        return self.root / f"{slug}-{str(workspace_id)[:8]}"

    async def _audit(
        self, event_type: str, workspace: WorkspaceEnvironment, actor: str, details: Dict[str, Any]
    ) -> None:
        self.db.add(
            AuditEvent(
                event_type=event_type,
                actor=actor,
                target=str(workspace.id),
                details={"workspace_id": str(workspace.id), "provider": workspace.provider, **details},
            )
        )

    async def create(
        self,
        *,
        name: str,
        project_id: Optional[str],
        provider: str,
        credential_env_var: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        if not name or not name.strip():
            raise WorkspaceError("name is required")
        if provider not in SUPPORTED_PROVIDERS:
            raise WorkspaceError(f"unsupported workspace provider: {provider}")
        selected_provider = select_provider(provider)
        fallback = selected_provider != provider
        credential_env_var = validate_credential_env_var(credential_env_var)
        remote_info = None
        if selected_provider != "local":
            remote_info = await remote_adapter_for(selected_provider).provision(
                name.strip(), actor
            )
        isolation = DEFAULT_ISOLATION.as_dict()
        if remote_info:
            isolation["provider_external_id"] = remote_info["external_id"]
        workspace = WorkspaceEnvironment(
            name=name.strip(),
            project_id=UUID(str(project_id)) if project_id else None,
            provider=selected_provider,
            status="provisioning",
            isolation=isolation,
            credential_env_var=credential_env_var,
            directory=(
                f"remote://{remote_info['external_id']}" if remote_info else ""
            ),
        )
        self.db.add(workspace)
        await self.db.flush()
        if remote_info is None:
            workspace.directory = str(self._directory(str(workspace.id), str(workspace.name)))  # type: ignore[assignment]
            self.root.mkdir(parents=True, exist_ok=True)
            Path(workspace.directory).mkdir(parents=True, exist_ok=True)
        await self._audit(
            "workspace_created",
            workspace,
            actor,
            {
                "name": workspace.name,
                "requested_provider": provider,
                "provider_fallback": fallback,
                "provider_external_id": remote_info["external_id"] if remote_info else None,
            },
        )
        await self.db.commit()
        await self.db.refresh(workspace)
        return self._serialize(workspace)

    async def _transition(self, workspace: WorkspaceEnvironment, status: str) -> None:
        allowed = STATUS_TRANSITIONS.get(str(workspace.status), ())
        if status not in allowed:
            raise WorkspaceError(
                f"cannot change workspace from '{workspace.status}' to '{status}'"
            )
        workspace.status = status  # type: ignore[assignment]

    async def start(self, workspace_id: str, actor: str) -> Dict[str, Any]:
        workspace = await self._workspace(workspace_id)
        await self._transition(workspace, "active")
        if workspace.provider != "local":
            adapter, external_id = self._remote(workspace)
            await adapter.start(external_id, actor)
        await self._audit("workspace_started", workspace, actor, {})
        await self.db.commit()
        return self._serialize(workspace)

    async def execute(
        self, workspace_id: str, command: str, actor: str
    ) -> Dict[str, Any]:
        if not settings.workspace_enabled:
            raise WorkspaceError("Workspace manager is disabled")
        workspace = await self._workspace(workspace_id)
        if workspace.status != "active":
            raise WorkspaceError("workspace must be active before execution")
        assert_provider_available(workspace.provider)  # type: ignore[arg-type]
        isolation: Any = workspace.isolation or {}
        validate_isolation(isolation)
        credentials = await self._active_credentials(str(workspace.id))
        check_command_hosts(command, credentials)
        env_names = [credential.secret_env_var for credential in credentials]
        if workspace.credential_env_var:
            env_names.append(workspace.credential_env_var)
        if workspace.provider == "local":
            outcome = await self.adapter.run(
                Path(workspace.directory), command, isolation, env_names  # type: ignore[arg-type]
            )
        else:
            remote, external_id = self._remote(workspace)
            outcome = await remote.execute(external_id, command, env_names, actor)
        workspace.last_output = str(outcome.get("stdout") or "")[:2000]  # type: ignore[assignment]
        for stream in ("stdout", "stderr"):
            content = str(outcome.get(stream) or "")
            for chunk in workspace_log_chunks(stream, content):
                self.db.add(
                    AuditEvent(
                        event_type="workspace_log",
                        actor=actor,
                        target=str(workspace.id),
                        details={
                            "workspace_id": str(workspace.id),
                            "stream": chunk["stream"],
                            "sequence": chunk["sequence"],
                            "content": chunk["content"],
                        },
                    )
                )
        await self._audit(
            "workspace_execution",
            workspace,
            actor,
            {
                "status": outcome["status"],
                "adapter": self.adapter.name if workspace.provider == "local" else workspace.provider,
                "credential_ids": [str(item.id) for item in credentials],
            },
        )
        await self.db.commit()
        return {"workspace_id": str(workspace.id), **outcome}

    async def save(self, workspace_id: str, actor: str) -> Dict[str, Any]:
        workspace = await self._workspace(workspace_id)
        await self._transition(workspace, "saved")
        if workspace.provider == "local":
            digest = workspace_digest(Path(workspace.directory))
        else:
            remote, external_id = self._remote(workspace)
            await remote.save(external_id, actor)
            digest = external_id
        isolation = dict(workspace.isolation or {})
        isolation["checksum"] = digest
        workspace.isolation = isolation  # type: ignore[assignment]
        await self._audit("workspace_saved", workspace, actor, {"checksum": digest})
        await self.db.commit()
        return self._serialize(workspace)

    async def destroy(self, workspace_id: str, actor: str) -> Dict[str, Any]:
        workspace = await self._workspace(workspace_id)
        await self._transition(workspace, "destroyed")
        if workspace.provider == "local":
            directory = Path(workspace.directory).resolve()
            if workspace.isolation and workspace.isolation.get("checksum"):
                if workspace_digest(directory) != workspace.isolation["checksum"]:
                    await self._audit(
                        "workspace_destroy_unsaved", workspace, actor, {"directory": str(directory)}
                    )
            if self.root.resolve() in directory.parents and directory.exists():
                shutil.rmtree(directory, ignore_errors=True)
        else:
            remote, external_id = self._remote(workspace)
            await remote.destroy(external_id, actor)
        await self._audit("workspace_destroyed", workspace, actor, {})
        await self.db.commit()
        return self._serialize(workspace)

    async def _active_credentials(self, workspace_id: str) -> List[WorkspaceCredential]:
        result = await self.db.execute(
            select(WorkspaceCredential).where(
                WorkspaceCredential.workspace_id == UUID(str(workspace_id)),
                WorkspaceCredential.is_active.is_(True),
                WorkspaceCredential.revoked_at.is_(None),
            )
        )
        now = datetime.now(timezone.utc)
        return [
            credential
            for credential in result.scalars().all()
            if credential.is_active
            and credential.revoked_at is None
            and _aware(credential.expires_at) > now
        ]

    async def issue_credential(
        self,
        workspace_id: str,
        *,
        purpose: str,
        secret_env_var: str,
        scopes: Optional[Dict[str, Any]],
        ttl_seconds: Optional[int],
        actor: str,
    ) -> Dict[str, Any]:
        workspace = await self._workspace(workspace_id)
        if workspace.status == "destroyed":
            raise WorkspaceError("cannot issue credentials for a destroyed workspace")
        if purpose not in CREDENTIAL_PURPOSES:
            raise WorkspaceError(f"unsupported credential purpose: {purpose}")
        secret_env_var = validate_credential_env_var(secret_env_var)  # type: ignore[assignment]
        if not secret_env_var:
            raise WorkspaceError("secret_env_var is required")
        ttl = max(60, min(int(ttl_seconds or settings.workspace_credential_ttl_seconds), 86400))
        credential = WorkspaceCredential(
            workspace_id=workspace.id,
            purpose=purpose,
            secret_env_var=secret_env_var,
            scopes=validate_credential_scopes(scopes),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl),
            is_active=True,
            revoked_at=None,
        )
        self.db.add(credential)
        await self._audit(
            "workspace_credential_issued",
            workspace,
            actor,
            {
                "credential_id": str(credential.id),
                "purpose": purpose,
                "secret_env_var": secret_env_var,
                "expires_at": credential.expires_at.isoformat(),
            },
        )
        await self.db.commit()
        return self._serialize_credential(credential)

    async def list_credentials(self, workspace_id: str) -> List[Dict[str, Any]]:
        await self._workspace(workspace_id)
        result = await self.db.execute(
            select(WorkspaceCredential).where(
                WorkspaceCredential.workspace_id == UUID(str(workspace_id))
            )
        )
        return [self._serialize_credential(row) for row in result.scalars().all()]

    async def revoke_credential(
        self, workspace_id: str, credential_id: str, actor: str
    ) -> Dict[str, Any]:
        workspace = await self._workspace(workspace_id)
        result = await self.db.execute(
            select(WorkspaceCredential).where(
                WorkspaceCredential.id == UUID(str(credential_id)),
                WorkspaceCredential.workspace_id == workspace.id,
            )
        )
        credential = result.scalar_one_or_none()
        if not credential:
            raise LookupError("credential not found")
        credential.is_active = False  # type: ignore[assignment]
        credential.revoked_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self._audit(
            "workspace_credential_revoked",
            workspace,
            actor,
            {"credential_id": str(credential.id), "purpose": credential.purpose},
        )
        await self.db.commit()
        return self._serialize_credential(credential)

    async def list(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(WorkspaceEnvironment))
        return [self._serialize(workspace) for workspace in result.scalars().all()]

    @staticmethod
    def _serialize_credential(credential: WorkspaceCredential) -> Dict[str, Any]:
        """Never include a secret value — only its name and scope metadata."""
        return {
            "id": str(credential.id),
            "workspace_id": str(credential.workspace_id),
            "purpose": credential.purpose,
            "secret_env_var": credential.secret_env_var,
            "scopes": credential.scopes or {},
            "issued_at": credential.issued_at.isoformat() if credential.issued_at else None,
            "expires_at": credential.expires_at.isoformat() if credential.expires_at else None,
            "revoked_at": credential.revoked_at.isoformat() if credential.revoked_at else None,
            "is_active": bool(credential.is_active),
        }

    @staticmethod
    def _serialize(workspace: WorkspaceEnvironment) -> Dict[str, Any]:
        return {
            "id": str(workspace.id),
            "name": workspace.name,
            "project_id": str(workspace.project_id) if workspace.project_id else None,
            "provider": workspace.provider,
            "status": workspace.status,
            "isolation": workspace.isolation or {},
            "credential_env_var": workspace.credential_env_var,
            "directory": workspace.directory,
            "created_at": workspace.created_at.isoformat() if workspace.created_at else None,
        }
