"""Execution adapters for the Skill Runtime.

The default adapter is a stub: nothing is executed. The Docker adapter runs a
single script inside a disposable container with no network, a read-only skill
mount, no new privileges, a non-root user and hard resource limits.
"""

import asyncio
import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings


class SkillRuntimeAdapterError(RuntimeError):
    """Raised when an execution plan cannot be run safely."""


@dataclass
class ExecutionPlan:
    skill_id: str
    skill_dir: Path
    script: Optional[str]
    arguments: Dict[str, Any]
    network: bool
    filesystem: str
    checksum: str


class SkillRuntimeAdapter(ABC):
    name = "abstract"

    @abstractmethod
    async def execute(self, plan: ExecutionPlan) -> Dict[str, Any]:
        ...


class StubAdapter(SkillRuntimeAdapter):
    """Simulates execution; used for policy testing and the default posture."""

    name = "stub"

    async def execute(self, plan: ExecutionPlan) -> Dict[str, Any]:
        return {
            "status": "completed",
            "dry_run": True,
            "adapter": self.name,
            "simulated": True,
            "skill_id": plan.skill_id,
            "script": plan.script,
            "arguments": plan.arguments,
        }


class DockerAdapter(SkillRuntimeAdapter):
    """Runs one script in an isolated, network-less container."""

    name = "docker"

    @staticmethod
    def _container_script(script: Optional[str]) -> Optional[str]:
        if script is None:
            return None
        path = Path(script)
        if path.is_absolute() or path.parts[0] != "scripts" or any(
            part in {".", ".."} for part in path.parts
        ):
            raise SkillRuntimeAdapterError("script must be a relative path under scripts/")
        return "/skill/" + path.as_posix()

    def _command(self, plan: ExecutionPlan) -> list:
        if plan.network:
            raise SkillRuntimeAdapterError(
                "network-enabled skill execution requires a separately configured "
                "isolated network and is not enabled in this deployment"
            )
        container_script = self._container_script(plan.script)
        if not container_script:
            raise SkillRuntimeAdapterError("Docker adapter requires a script path")
        arguments = json.dumps(plan.arguments or {}, separators=(",", ":"))
        if len(arguments) > 8192:
            raise SkillRuntimeAdapterError("arguments are too large")
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
            "--pids-limit",
            "64",
            "--memory",
            settings.skill_runtime_memory,
            "--cpus",
            str(settings.skill_runtime_cpus),
            "-e",
            f"IAM_SKILL_ARGUMENTS={arguments}",
            "-v",
            f"{plan.skill_dir.resolve()}:/skill:ro",
            settings.skill_runtime_image,
            "python",
            container_script,
        ]

    async def execute(self, plan: ExecutionPlan) -> Dict[str, Any]:
        command = self._command(plan)
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                capture_output=True,
                text=True,
                timeout=settings.skill_runtime_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise SkillRuntimeAdapterError("execution timed out")
        except OSError as exc:
            raise SkillRuntimeAdapterError(f"docker unavailable: {type(exc).__name__}") from exc
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "dry_run": False,
            "adapter": self.name,
            "exit_code": result.returncode,
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-4000:],
        }


def adapter_for(name: str):
    if name == "stub":
        return StubAdapter()
    if name == "docker":
        return DockerAdapter()
    raise SkillRuntimeAdapterError(f"unknown Skill Runtime adapter: {name}")
