"""Colab MCP driver for the research coordinator (OD-41 / WP5).

The backend cannot call MCP tools directly; an agent-side bridge injects a
`tool_caller` that dispatches to `tools.colab.*`. This module contains only the
protocol logic: quota discovery, runtime reuse/creation, sessions, cell
execution, result collection and cleanup. It is testable with a stub caller.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..free_sandboxes.base import (
    EnvironmentState,
    SandboxError,
    WorkloadRequest,
)
from .adapters import ResearchDriver

MCPToolCaller = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]


class ColabMCPDriver:
    """Implements `ResearchDriver` over the hosted Colab MCP endpoint."""

    def __init__(
        self,
        tool_caller: MCPToolCaller,
        preferred_accelerators: tuple[str, ...] = ("T4", "L4", "A100"),
    ) -> None:
        self.call = tool_caller
        self.preferred = preferred_accelerators
        self._sessions: Dict[str, str] = {}
        self._created_runtimes: set[str] = set()

    async def tool(self, tool_name: str, **args: Any) -> Dict[str, Any]:
        return await self.call(tool_name, args)

    # ---------------------------------------------------------------- discovery
    async def subscription(self) -> Dict[str, Any]:
        return await self.tool("get_subscription")

    async def runtime_specs(self) -> List[dict]:
        data = await self.tool("list_runtime_specs")
        return list(data.get("runtimeSpecs") or [])

    async def runtimes(self) -> List[dict]:
        data = await self.tool("list_runtimes")
        return list(data.get("runtimes") or [])

    def pick_gpu_spec(self, specs: List[dict], shape: str = "SHAPE_STANDARD") -> dict:
        for accelerator in self.preferred:
            for spec in specs:
                key = spec.get("key") or {}
                if (
                    spec.get("eligible")
                    and key.get("accelerator") == accelerator
                    and key.get("variant") == "VARIANT_GPU"
                ):
                    return key
        raise SandboxError("no eligible GPU runtime spec on the free tier")

    # ---------------------------------------------------------------- lifecycle
    async def provision(self, request: WorkloadRequest) -> str:
        """Reuse an eligible GPU runtime, otherwise create one."""
        for runtime in await self.runtimes():
            key = (runtime.get("runtimeSpec") or {}).get("key") or {}
            if key.get("variant") == "VARIANT_GPU" and runtime.get("name"):
                return str(runtime["name"])

        spec = self.pick_gpu_spec(await self.runtime_specs())
        created = await self.tool(
            "create_runtime",
            requestId=str(uuid.uuid4()),
            runtime={"runtimeSpec": spec},
        )
        name = created.get("name")
        if not name:
            raise SandboxError("create_runtime returned no runtime name")
        self._created_runtimes.add(name)
        return str(name)

    async def start(self, external_id: str) -> None:
        result = await self.tool(
            "create_session",
            parent=external_id,
            sessionId=f"iam-{uuid.uuid4().hex[:8]}",
        )
        name = result.get("name")
        if not name:
            raise SandboxError("create_session returned no session name")
        self._sessions[external_id] = str(name)

    async def status(self, external_id: str) -> EnvironmentState:
        for runtime in await self.runtimes():
            if runtime.get("name") == external_id:
                return EnvironmentState.RUNNING
        return EnvironmentState.STOPPED

    async def execute(self, external_id: str, code: str) -> Dict[str, Any]:
        session = self._sessions.get(external_id)
        if not session:
            raise SandboxError(f"no open session for runtime {external_id}")
        return await self.tool(
            "execute_code",
            session=session,
            code=code,
            executionId=str(uuid.uuid4()),
        )

    async def execute_cells(self, external_id: str, cells: List[str]) -> List[Dict[str, Any]]:
        outputs = []
        for cell in cells:
            result = await self.execute(external_id, cell)
            if result.get("executionError"):
                raise SandboxError(
                    f"Colab execution failed: {result['executionError']}"
                )
            outputs.append(result)
        return outputs

    async def collect(self, external_id: str) -> Dict[str, Any]:
        """Read a result JSON written by the notebook into the runtime."""
        output = await self.execute(
            external_id,
            "print(open('/content/iam_result.json', encoding='utf-8').read())",
        )
        text = output.get("stdout") or ""
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise SandboxError("Colab result file was not valid JSON") from exc

    async def cleanup(self, external_id: str, delete_runtime: bool = False) -> None:
        session = self._sessions.pop(external_id, None)
        if session:
            await self.tool("delete_session", name=session)
        if delete_runtime and external_id in self._created_runtimes:
            await self.tool("delete_runtime", name=external_id)
            self._created_runtimes.discard(external_id)


# Explicit conformance check for the research-driver protocol.
_: ResearchDriver = ColabMCPDriver  # type: ignore[assignment]
