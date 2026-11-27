"""The shipped MCP bridge process is fail-closed without a dispatcher."""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


def _load_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "mcp_bridge_server.py"
    spec = importlib.util.spec_from_file_location("mcp_bridge_server", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


bridge = _load_module()


class MCPBridgeServerTests(unittest.TestCase):
    def test_no_dispatcher_by_default(self):
        with patch.dict("os.environ", {"COLAB_MCP_DISPATCHER": ""}, clear=False):
            self.assertIsNone(bridge.load_dispatcher())

    def test_invalid_dispatcher_spec_is_rejected(self):
        with patch.dict(
            "os.environ", {"COLAB_MCP_DISPATCHER": "not-a-callable-spec"}, clear=False
        ):
            with self.assertRaises(ValueError):
                bridge.load_dispatcher()

    def test_only_known_colab_tools_are_allowed(self):
        self.assertIn("execute_code", bridge.TOOLS)
        self.assertNotIn("spend_money", bridge.TOOLS)


if __name__ == "__main__":
    unittest.main()
