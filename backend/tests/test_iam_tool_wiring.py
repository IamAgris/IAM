"""IAM and Qwen can reach registered backend capability tools, fail-closed.

These tests cover the wiring, not the provider: no web or model call is made.
"""

import json
import re
import unittest
from unittest.mock import AsyncMock, patch

from app.orchestration import dispatch as action_dispatch
from app.services.iam_tool_executor import execute_registered_tool
from app.services.iam_tool_manifest import (
    EXECUTABLE_IICS_TOOLS,
    executable_tool_names,
    model_tool_schemas,
    resolve_wire_name,
    wire_name,
)
from app.services.model_inference import inference_service
from app.services.tool_authorization import ToolAuthorizationError


class IAMToolWiringTests(unittest.IsolatedAsyncioTestCase):
    def test_all_five_legacy_capabilities_are_executable(self):
        names = executable_tool_names()
        expected = {
            "tone.analyze",
            "network.inspect",
            "sandbox.status",
            "finance.research.read",
            *EXECUTABLE_IICS_TOOLS,
        }
        self.assertTrue(expected <= names, f"missing tools: {expected - names}")

    def test_schemas_are_function_tools_with_bounded_properties(self):
        schemas = model_tool_schemas()
        self.assertTrue(schemas)
        for schema in schemas:
            self.assertEqual(schema["type"], "function")
            function = schema["function"]
            self.assertTrue(function["name"])
            self.assertTrue(function["description"])
            self.assertEqual(function["parameters"]["type"], "object")
            self.assertIsInstance(function["parameters"]["properties"], dict)

    def test_schema_names_are_provider_safe(self):
        # LiteLLM/OpenAI reject dots in function names; Ollama allows them.
        for schema in model_tool_schemas():
            name = schema["function"]["name"]
            self.assertRegex(name, r"^[A-Za-z0-9_-]+$")
            self.assertEqual(resolve_wire_name(name) in executable_tool_names(), True)

    def test_wire_names_round_trip_to_registered_names(self):
        for registered in executable_tool_names():
            self.assertEqual(resolve_wire_name(wire_name(registered)), registered)

    def test_approval_bearing_iics_tools_are_not_offered(self):
        names = executable_tool_names()
        self.assertNotIn("iics.creator.approval_request", names)
        self.assertNotIn("iics.authorize", names)
        self.assertNotIn("iics.qa.run", names)

    async def test_executor_fails_closed_without_database(self):
        outcome = await execute_registered_tool(
            None, "tone.analyze", {"text": "hello"}
        )
        self.assertIn("authorization unavailable", outcome["error"])

    async def test_executor_rejects_unknown_tool(self):
        outcome = await execute_registered_tool(
            object(), "shell.exec", {"command": "rm -rf /"}
        )
        self.assertIn("not permitted", outcome["error"])

    async def test_authorization_refusal_is_surfaced(self):
        refusal = ToolAuthorizationError("tool_is_blocked", "tool_blocked")
        with patch(
            "app.services.tool_authorization.authorize_tool_call",
            new=AsyncMock(side_effect=refusal),
        ):
            outcome = await execute_registered_tool(
                object(), "network.inspect", {}
            )
        self.assertEqual(outcome["code"], "tool_blocked")

    async def test_inference_routes_non_web_tool_to_gated_executor(self):
        executed = AsyncMock(return_value={"status": "analysed", "tone": "neutral"})
        call = {
            "name": "tone.analyze",
            "arguments": json.dumps({"text": "A calm, careful message."}),
        }
        with patch(
            "app.services.iam_tool_executor.execute_registered_tool",
            new=executed,
        ):
            outcome = await inference_service.execute_tool_call(call, db=object())
        self.assertEqual(outcome["status"], "analysed")
        executed.assert_awaited_once()
        args = executed.await_args.args
        self.assertEqual(args[1], "tone.analyze")
        self.assertEqual(args[2]["text"], "A calm, careful message.")

    async def test_inference_resolves_provider_safe_name_to_registered_tool(self):
        executed = AsyncMock(return_value={"status": "ok"})
        call = {"name": wire_name("network.inspect"), "arguments": "{}"}
        with patch(
            "app.services.iam_tool_executor.execute_registered_tool",
            new=executed,
        ):
            await inference_service.execute_tool_call(call, db=object())
        self.assertEqual(executed.await_args.args[1], "network.inspect")

    async def test_brain_tool_actions_are_allowlisted_and_fail_safely(self):
        for action in (
            "tone_analyze",
            "network_inspect",
            "sandbox_status",
            "finance_research_read",
            "iics_egress_check",
        ):
            self.assertIn(action, action_dispatch.AVAILABLE)
            result = await action_dispatch.dispatch(
                None, action, {"text": "hello", "url": "https://example.org"}
            )
            self.assertEqual(result["status"], "failure")
            self.assertEqual(result["service"], "IAMToolExecutor")
