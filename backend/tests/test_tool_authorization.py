"""Tests for the tool-permission gate used by the autonomy graph."""

import unittest
from types import SimpleNamespace

from starlette.requests import Request

from app.core.error_response import error_response
from app.services.tool_authorization import (
    ToolAuthorizationError,
    authorize_tool_call,
)


class FakeDB:
    """Returns queued scalar results in call order."""

    def __init__(self, tool, permission):
        self.tool = tool
        self.permission = permission
        self.calls = 0

    async def execute(self, statement):
        self.calls += 1
        value = self.tool if self.calls == 1 else self.permission
        # Mirror the is_active filter in the real SQL query.
        if self.calls == 1 and not getattr(value, "is_active", True):
            value = None
        return SimpleNamespace(scalar_one_or_none=lambda: value)


def tool(active=True, name="demo"):
    return SimpleNamespace(id="tool-1", name=name, is_active=active)


def permission(level="autonomous", approval=False):
    return SimpleNamespace(
        tool_id="tool-1",
        permission_level=level,
        requires_human_approval=approval,
    )


class ToolAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_tool_is_refused(self):
        with self.assertRaises(ToolAuthorizationError) as caught:
            await authorize_tool_call(FakeDB(None, None), "missing")
        self.assertEqual(caught.exception.code, "unknown_tool")

    async def test_inactive_tool_is_refused(self):
        with self.assertRaises(ToolAuthorizationError):
            await authorize_tool_call(FakeDB(tool(active=False), permission()), "demo")

    async def test_missing_permission_is_refused(self):
        with self.assertRaises(ToolAuthorizationError) as caught:
            await authorize_tool_call(FakeDB(tool(), None), "demo")
        self.assertEqual(caught.exception.code, "tool_blocked")

    async def test_blocked_tool_is_refused(self):
        with self.assertRaises(ToolAuthorizationError) as caught:
            await authorize_tool_call(FakeDB(tool(), permission("blocked")), "demo")
        self.assertEqual(caught.exception.code, "tool_blocked")

    async def test_explicit_level_requires_signed_approval(self):
        with self.assertRaises(ToolAuthorizationError) as caught:
            await authorize_tool_call(FakeDB(tool(), permission("explicit")), "demo")
        self.assertEqual(caught.exception.code, "approval_required")
        granted = await authorize_tool_call(
            FakeDB(tool(), permission("explicit")),
            "demo",
            signed_authorization={"authorized": True, "authorization_id": "auth-1"},
        )
        self.assertEqual(granted, "explicit")

    async def test_human_approval_flag_is_enforced(self):
        with self.assertRaises(ToolAuthorizationError) as caught:
            await authorize_tool_call(FakeDB(tool(), permission("authorized", True)), "demo")
        self.assertEqual(caught.exception.code, "approval_required")
        granted = await authorize_tool_call(
            FakeDB(tool(), permission("authorized", True)),
            "demo",
            signed_authorization={"authorized": True, "authorization_id": "auth-2"},
        )
        self.assertEqual(granted, "authorized")

    async def test_bare_approval_boolean_is_not_signed_authority(self):
        from unittest.mock import AsyncMock, patch

        from app.services.creatorapproval_service import CreatorApprovalService

        with patch.object(
            CreatorApprovalService,
            "check_authorization",
            new=AsyncMock(return_value={"authorized": False}),
        ):
            with self.assertRaises(ToolAuthorizationError) as caught:
                await authorize_tool_call(
                    FakeDB(tool(), permission("explicit")),
                    "demo",
                    approval_granted=True,
                )
        self.assertEqual(caught.exception.code, "approval_required")

    async def test_autonomous_tool_is_allowed(self):
        self.assertEqual(
            await authorize_tool_call(FakeDB(tool(), permission()), "demo"),
            "autonomous",
        )


class ErrorEnvelopeTests(unittest.TestCase):
    def test_contract_fields_are_present(self):
        request = Request({"type": "http", "headers": [], "path": "/"})
        response = error_response(
            request=request,
            status_code=401,
            detail="Missing or invalid API credential",
            code="unauthorized",
        )
        payload = response.body.decode()
        self.assertIn('"detail"', payload)
        self.assertIn('"code"', payload)
        self.assertIn('"request_id"', payload)


if __name__ == "__main__":
    unittest.main()
