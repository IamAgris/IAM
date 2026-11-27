"""Optional HTTP bridge to the agent-side MCP tool caller (OD-41 / OD-51).

The backend cannot call MCP tools directly. When an operator supplies a local
bridge endpoint, this caller dispatches ``tools.colab.*`` calls over HTTP and
returns only structured results. Without configuration it is disabled, so the
research adapters fail closed as before rather than fabricating a runtime.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings

from .base import ResearchError


class MCPBridgeError(ResearchError):
    """The configured MCP bridge is unusable or returned an error."""


class HttpMCPToolCaller:
    def __init__(
        self,
        endpoint: str,
        *,
        token_env: str = "COLAB_MCP_BRIDGE_TOKEN",
        timeout: float = 60.0,
    ) -> None:
        if not endpoint.strip():
            raise MCPBridgeError("MCP bridge endpoint is required")
        self.endpoint = endpoint.strip()
        self.token_env = token_env
        self.timeout = timeout

    async def __call__(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        token = os.environ.get(self.token_env, "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint,
                    json={"tool": tool_name, "arguments": args},
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise MCPBridgeError(f"MCP bridge call failed: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise MCPBridgeError(f"MCP bridge returned {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise MCPBridgeError("MCP bridge returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise MCPBridgeError("MCP bridge returned a non-object result")
        if payload.get("error"):
            raise MCPBridgeError(str(payload["error"])[:300])
        result = payload.get("result")
        return result if isinstance(result, dict) else payload


def default_tool_caller() -> Optional[HttpMCPToolCaller]:
    """Build the configured MCP caller, or None when no bridge is provisioned."""
    if not settings.colab_mcp_enabled or not settings.colab_mcp_bridge_url:
        return None
    return HttpMCPToolCaller(
        settings.colab_mcp_bridge_url, token_env=settings.colab_mcp_bridge_token_env
    )
