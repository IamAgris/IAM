"""MCP bridge: disabled by default, fail closed when the configured bridge errors."""

import unittest
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.ai_research import mcp_bridge


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload or {}

    def json(self):
        return self.payload


class FakeClient:
    last = None

    def __init__(self, *_args, **_kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def post(self, url, json, headers):
        FakeClient.last = (url, json, headers)
        return FakeClient.response


class MCPBridgeTests(unittest.IsolatedAsyncioTestCase):
    def test_disabled_by_default(self):
        with patch.object(settings, "colab_mcp_enabled", False):
            self.assertIsNone(mcp_bridge.default_tool_caller())

    async def test_bridge_dispatches_and_returns_result(self):
        FakeClient.response = FakeResponse(payload={"result": {"name": "runtimes", "ok": True}})
        caller = mcp_bridge.HttpMCPToolCaller("http://bridge.local/mcp")
        with patch.object(mcp_bridge.httpx, "AsyncClient", FakeClient):
            result = await caller("list_runtimes", {})
        self.assertEqual(result, {"name": "runtimes", "ok": True})
        self.assertEqual(FakeClient.last[1]["tool"], "list_runtimes")

    async def test_bridge_error_fails_closed(self):
        FakeClient.response = FakeResponse(status_code=500)
        caller = mcp_bridge.HttpMCPToolCaller("http://bridge.local/mcp")
        with patch.object(mcp_bridge.httpx, "AsyncClient", FakeClient):
            with self.assertRaises(mcp_bridge.MCPBridgeError):
                await caller("list_runtimes", {})


if __name__ == "__main__":
    unittest.main()
