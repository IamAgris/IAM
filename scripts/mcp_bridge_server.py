"""Local HTTP bridge for agent-side MCP tool dispatch.

Ships the process that ``HttpMCPToolCaller`` talks to. It is fail-closed: no
dispatcher means every request is refused. The operator supplies a dispatcher
callable that has access to the signed-in MCP tools, e.g.
``my_package.bridge:dispatch(tool_name, arguments) -> dict``.

Environment:
    COLAB_MCP_BRIDGE_BIND      host:port (default 127.0.0.1:8788)
    COLAB_MCP_BRIDGE_TOKEN     required bearer token (never logged)
    COLAB_MCP_DISPATCHER       module:callable import path

Usage:
    python scripts/mcp_bridge_server.py
"""

from __future__ import annotations

import importlib
import json
import os
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

TOOLS = frozenset(
    {
        "get_subscription",
        "list_runtime_specs",
        "list_runtimes",
        "get_runtime",
        "create_runtime",
        "create_session",
        "list_sessions",
        "delete_session",
        "execute_code",
        "delete_runtime",
    }
)


def load_dispatcher() -> Callable[[str, dict[str, Any]], dict[str, Any]] | None:
    spec = os.environ.get("COLAB_MCP_DISPATCHER", "").strip()
    if not spec:
        return None
    module_name, _, function_name = spec.partition(":")
    if not module_name or not function_name:
        raise ValueError("COLAB_MCP_DISPATCHER must be module:callable")
    function = getattr(importlib.import_module(module_name), function_name)
    if not callable(function):
        raise TypeError("COLAB_MCP_DISPATCHER target is not callable")
    return function


class BridgeHandler(BaseHTTPRequestHandler):
    dispatcher: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None

    def _reply(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/mcp":
            self._reply(404, {"error": "not_found"})
            return
        expected = os.environ.get("COLAB_MCP_BRIDGE_TOKEN", "").strip()
        if not expected or self.headers.get("Authorization") != f"Bearer {expected}":
            self._reply(401, {"error": "unauthorized"})
            return
        if self.dispatcher is None:
            self._reply(503, {"error": "no_mcp_dispatcher_configured"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, TypeError):
            self._reply(400, {"error": "invalid_json"})
            return
        tool = str(payload.get("tool") or "").strip()
        args = payload.get("arguments") or {}
        if tool not in TOOLS or not isinstance(args, dict):
            self._reply(400, {"error": "invalid_tool_call"})
            return
        try:
            result = self.dispatcher(tool, args)
        except Exception as exc:  # noqa: BLE001 - operator dispatcher is arbitrary code
            self._reply(502, {"error": f"dispatcher_failed: {type(exc).__name__}"})
            return
        if not isinstance(result, dict):
            self._reply(502, {"error": "dispatcher_returned_non_object"})
            return
        self._reply(200, {"result": result})

    def log_message(self, *_args: Any) -> None:
        return  # never log tokens, prompts or tool arguments


def main() -> None:
    bind = os.environ.get("COLAB_MCP_BRIDGE_BIND", "127.0.0.1:8788")
    host, _, port = bind.partition(":")
    dispatcher = load_dispatcher()
    BridgeHandler.dispatcher = dispatcher
    server = ThreadingHTTPServer((host, int(port or 8788)), BridgeHandler)
    print(f"mcp_bridge listening on {host}:{port} dispatcher={'yes' if dispatcher else 'no'}")
    server.serve_forever()


if __name__ == "__main__":
    main()
