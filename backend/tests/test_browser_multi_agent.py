"""Doc 29 P7 tests: isolated agent sessions, handover, recovery and sharing."""

import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.routes import browser_agents as agents_routes
from app.core.config import settings
from app.models.uwaie import WebsiteWorkflow
from app.models.web_knowledge import BrowserAgentSession
from app.services.browser_multi_agent import BrowserMultiAgentError, BrowserMultiAgentService


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None


class FakeDB:
    def __init__(self):
        self.rows = []

    def add(self, obj):
        if obj not in self.rows:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.rows.append(obj)

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        rows = [r for r in self.rows if isinstance(r, entity)]
        where = getattr(statement, "whereclause", None)
        if where is not None and hasattr(where, "left") and hasattr(where.left, "key"):
            key = where.left.key
            value = getattr(where.right, "value", None)
            rows = [r for r in rows if getattr(r, key, None) == value]
        return FakeResult(rows)


def service_with_db(db):
    service = BrowserMultiAgentService(db)
    service.evidence = MagicMock()
    service.evidence.append_audit = AsyncMock(return_value="audit-1")
    return service


def browser_mock():
    browser = MagicMock()
    browser.open_session = AsyncMock(return_value={"engine": "chromium", "actor_type": "agent"})
    browser.close_session = AsyncMock(return_value=True)
    page = MagicMock()
    page.is_closed = lambda: True
    browser.get_persistent_page = AsyncMock(return_value=page)
    return browser


class MultiAgentTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = service_with_db(self.db)
        self.patches = [
            patch.object(settings, "browser_max_concurrent_sessions", 1),
            patch("app.services.browser_multi_agent.browser_service", browser_mock()),
            patch("app.services.browser_multi_agent.IRWM"),
        ]
        started = [item.start() for item in self.patches]
        started[2].status = MagicMock(return_value={"available": True})

    async def asyncTearDown(self):
        for item in reversed(self.patches):
            item.stop()

    async def test_capacity_respects_browser_cap(self):
        self.db.add(BrowserAgentSession(
            agent_id="a1", session_token="s1", owner="a1", state="open"
        ))
        capacity = await self.service.capacity()
        self.assertFalse(capacity["can_admit"])
        self.assertEqual(capacity["open_sessions"], 1)

    async def test_open_for_agent_is_isolated_and_attributed(self):
        with patch("app.services.browser_multi_agent.IRWM"):
            result = await self.service.open_for_agent(
                "a2", mode="isolated", permission_scope=["browse_public"], task_id="t1"
            )
        self.assertEqual(result["agent_id"], "a2")
        self.assertEqual(result["isolation_level"], "isolated")
        self.assertTrue(result["session_id"].startswith("agent-"))

    async def test_agent_cannot_reuse_another_session(self):
        with patch("app.services.browser_multi_agent.IRWM"):
            await self.service.open_for_agent("a3")
        with patch("app.services.browser_multi_agent.IRWM"):
            with self.assertRaises(BrowserMultiAgentError):
                await self.service.open_for_agent("a3")

    async def test_transfer_requires_signed_approval(self):
        self.db.add(BrowserAgentSession(
            agent_id="a4", session_token="s4", owner="a4", state="open"
        ))
        with patch(
            "app.services.browser_multi_agent.CreatorApprovalService"
        ) as approval_cls:
            approval_cls.return_value.check_authorization = AsyncMock(
                return_value={"authorized": False}
            )
            with self.assertRaises(BrowserMultiAgentError):
                await self.service.transfer(
                    "s4", from_agent="a4", to_agent="a5", authorization_id="auth-1"
                )
            approval_cls.return_value.check_authorization = AsyncMock(
                return_value={"authorized": True}
            )
            result = await self.service.transfer(
                "s4", from_agent="a4", to_agent="a5", authorization_id="auth-1"
            )
        self.assertEqual(result["agent_id"], "a5")

    async def test_takeover_uses_hais_level_4(self):
        self.db.add(BrowserAgentSession(
            agent_id="a6", session_token="s6", owner="a6", state="open", task_id="t6"
        ))
        with patch("app.services.browser_multi_agent.HumanAssistanceService") as hais_cls:
            hais_cls.return_value.request = AsyncMock(return_value={"id": "r1", "level": "4"})
            result = await self.service.request_takeover("s6", reason="captcha")
        self.assertEqual(result["level"], "4")
        self.assertEqual(
            hais_cls.return_value.request.await_args.kwargs["level"], "4"
        )

    async def test_recovery_reopens_closed_session(self):
        self.db.add(BrowserAgentSession(
            agent_id="a7", session_token="s7", owner="a7", state="recovering",
            isolation_level="isolated", permission_scope=["browse_public"],
        ))
        result = await self.service.recover("s7")
        self.assertTrue(result["reopened"])

    async def test_workflow_sharing_requires_approval(self):
        workflow_id = uuid.uuid4()
        self.db.add(WebsiteWorkflow(
            id=workflow_id, name="unapproved", url_pattern="https://example.com/*",
            steps=[], source_actor="iam", is_approved=False,
        ))
        with self.assertRaises(BrowserMultiAgentError):
            await self.service.share_approved_workflow(
                str(workflow_id), from_agent="a8", to_agent="a9"
            )
        workflow = [r for r in self.db.rows if isinstance(r, WebsiteWorkflow)][0]
        workflow.is_approved = True
        result = await self.service.share_approved_workflow(
            str(workflow_id), from_agent="a8", to_agent="a9"
        )
        self.assertTrue(result["credential_free"])
        self.assertEqual(result["shared_with"], "a9")


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_capacity_route_delegates(self):
        request = SimpleNamespace(state=SimpleNamespace(credential=None))
        with patch.object(agents_routes, "BrowserMultiAgentService") as service_cls:
            service_cls.return_value.capacity = AsyncMock(return_value={"can_admit": True})
            result = await agents_routes.capacity(object())
        self.assertTrue(result["can_admit"])


if __name__ == "__main__":
    unittest.main()
