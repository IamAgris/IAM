"""Transport adapters for external security engines.

Only the documented ARTEX built-in MCP surface is modelled: Streamable HTTP,
stateless JSON-only, bearer token, scoped tools at `<base_url>/mcp`. Nothing is
called unless the IAM Security Guard has already approved the tool.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict
from urllib.parse import urljoin

import httpx

from app.services.cybersecurity.security_guard import SecurityGuardDenied


class SecurityEngineAdapter(ABC):
    """Transport boundary. Implementations must never self-authorise."""

    @abstractmethod
    async def call_tool(
        self, config: Dict[str, Any], tool: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        ...

    async def health_check(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return await self.call_tool(config, "list_tasks", {})


class StubAdapter(SecurityEngineAdapter):
    """Always-local adapter for testing and policy dry runs."""

    async def call_tool(
        self, config: Dict[str, Any], tool: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "dry_run": True,
            "transport": "stub",
            "tool": tool,
            "arguments": arguments,
            "result": {"tasks": [], "findings": []},
        }


class ArtexMcpAdapter(SecurityEngineAdapter):
    """ARTEX built-in MCP server (v0.3.30+), Streamable HTTP, stateless JSON."""

    async def call_tool(
        self, config: Dict[str, Any], tool: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        if config.get("dry_run", True):
            return {
                "dry_run": True,
                "transport": "mcp_streamable_http",
                "tool": tool,
                "arguments": arguments,
                "result": {"simulated": True},
            }

        token_env = config.get("token_env_var") or "ARTEX_MCP_TOKEN"
        token = os.environ.get(token_env)
        if not token:
            raise SecurityGuardDenied(
                f"MCP access token is not configured in environment variable {token_env}"
            )

        base_url = config["base_url"].rstrip("/") + "/"
        endpoint = urljoin(base_url, str(config.get("mcp_path", "/mcp")).lstrip("/"))
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=False) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            raise SecurityGuardDenied(f"engine transport failed: {type(exc).__name__}") from exc

        if response.status_code != 200:
            # Never echo headers or body: they may contain tokens or target data.
            raise SecurityGuardDenied(f"engine rejected the call (HTTP {response.status_code})")
        try:
            body = response.json()
        except ValueError as exc:
            raise SecurityGuardDenied("engine returned a non-JSON response") from exc
        if body.get("error"):
            raise SecurityGuardDenied("engine returned a JSON-RPC error")
        return {"dry_run": False, "transport": "mcp_streamable_http", "tool": tool, "result": body.get("result", {})}


def adapter_for(transport: str) -> SecurityEngineAdapter:
    if transport == "artex_mcp" or transport == "mcp_streamable_http":
        return ArtexMcpAdapter()
    if transport == "stub":
        return StubAdapter()
    raise SecurityGuardDenied(f"unsupported transport: {transport}")
