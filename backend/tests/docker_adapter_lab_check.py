"""Manual lab check for the Docker Skill Runtime adapter.

Runs two real scripts in a disposable no-network container using an image that
already exists locally. This is intentionally not part of CI: CI runners may not
have the image or Docker daemon available.

Usage:  python tests/docker_adapter_lab_check.py
Override image with SKILL_RUNTIME_TEST_IMAGE=<image>:<tag>.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

from app.core.config import settings
from app.services.skillruntime.adapters import DockerAdapter, ExecutionPlan

HELLO = "print('IAM_RUNTIME_LAB_OK')\n"
NETCHECK = (
    "import socket\n"
    "try:\n"
    "    socket.create_connection(('1.1.1.1', 80), timeout=1)\n"
    "    print('NETWORK_OK')\n"
    "except OSError:\n"
    "    print('NETWORK_BLOCKED')\n"
)


async def run(root: Path, name: str, source: str) -> dict:
    script_dir = root / "scripts"
    script_dir.mkdir(exist_ok=True)
    script = script_dir / f"{name}.py"
    script.write_text(source, encoding="utf-8")
    plan = ExecutionPlan(
        skill_id=f"iam.native.lab.{name}",
        skill_dir=root,
        script=f"scripts/{name}.py",
        arguments={},
        network=False,
        filesystem="none",
        checksum="lab",
    )
    return await DockerAdapter().execute(plan)


async def main() -> None:
    settings.skill_runtime_adapter = "docker"
    settings.skill_runtime_enabled = True
    settings.skill_runtime_image = os.environ.get(
        "SKILL_RUNTIME_TEST_IMAGE", "project-aura-backend:latest"
    )
    settings.skill_runtime_timeout_seconds = 45

    with tempfile.TemporaryDirectory(prefix="iam-runtime-lab-") as tmp:
        root = Path(tmp)
        hello = await run(root, "hello", HELLO)
        print(f"hello: exit={hello.get('exit_code')} stdout={hello.get('stdout', '').strip()!r}")
        assert hello["status"] == "completed", hello
        assert "IAM_RUNTIME_LAB_OK" in hello["stdout"]

        network = await run(root, "netcheck", NETCHECK)
        print(
            f"netcheck: exit={network.get('exit_code')} "
            f"stdout={network.get('stdout', '').strip()!r}"
        )
        assert network["status"] == "completed", network
        assert "NETWORK_BLOCKED" in network["stdout"]
        assert "NETWORK_OK" not in network["stdout"]

    print("DOCKER ADAPTER LAB CHECK PASSED")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
