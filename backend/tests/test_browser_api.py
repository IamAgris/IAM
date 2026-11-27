"""Doc 29 WP-05 tests: /api/v1/browser envelope endpoints."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api.routes import browser as browser_routes
from app.core.auth_policy import required_scope
from app.services.browser_evidence_service import BrowserEvidenceError

REQUEST = SimpleNamespace(state=SimpleNamespace(credential=None))
DB = object()


class BrowserApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_browser_prefix_requires_admin_scope(self):
        self.assertEqual(required_scope("/api/v1/browser/tasks"), "admin")
        self.assertEqual(required_scope("/api/v1/browser/sessions"), "admin")

    async def test_create_task_returns_standard_envelope(self):
        payload = browser_routes.TaskRequest(
            task_id="task-api-1",
            steps=[{"action": "navigate", "target": "https://example.com"}],
            verification={"expected_text": "Example Domain"},
            session_token="session-1",
        )
        with patch.object(browser_routes.settings, "browser_task_worker_backend", "loop"), \
             patch.object(browser_routes, "BrowserEvidenceService") as evidence_cls, \
             patch.object(browser_routes, "UWAIEService") as uwaie_cls:
            evidence = evidence_cls.return_value
            evidence.start_run = AsyncMock(return_value={"task_id": "task-api-1", "state": "queued"})
            evidence.envelope = AsyncMock(return_value={
                "task_id": "task-api-1", "status": "completed", "evidence_refs": ["e1"],
                "actor": "sdk", "actor_type": "agent",
            })
            uwaie_cls.return_value.execute = AsyncMock(return_value={
                "verified": True,
                "envelope": {
                    "task_id": "task-api-1", "status": "completed", "evidence_refs": ["e1"],
                    "actor": "sdk", "actor_type": "agent",
                },
            })
            result = await browser_routes.create_task(payload, REQUEST, DB)
        self.assertEqual(result["task_id"], "task-api-1")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["evidence_refs"], ["e1"])

    async def test_open_session_passes_mode_and_attribution(self):
        payload = browser_routes.SessionRequest(mode="isolated", permission_scope=["browse_public"])
        with patch.object(browser_routes, "UWAIEService") as uwaie_cls, \
             patch.object(browser_routes, "browser_service") as browser, \
             patch.object(browser_routes, "InternetAccessService"):
            uwaie_cls.return_value.create_session = AsyncMock(
                return_value={"session_token": "session-2"}
            )
            browser.open_session = AsyncMock(return_value={
                "session_id": "session-2", "mode": "isolated", "actor_type": "agent",
            })
            result = await browser_routes.open_session(payload, REQUEST, DB)
        self.assertEqual(result["status"], "open")
        self.assertEqual(result["mode"], "isolated")
        browser.open_session.assert_awaited_once_with(
            "session-2", mode="isolated", owner="agent",
            permission_scope=["browse_public"],
        )

    async def test_cancel_task_closes_session_and_records_status(self):
        with patch.object(browser_routes, "BrowserEvidenceService") as evidence_cls, \
             patch.object(browser_routes, "browser_service") as browser:
            evidence = evidence_cls.return_value
            evidence.set_state = AsyncMock(return_value={"session_id": "session-3", "state": "cancelled"})
            evidence.append_audit = AsyncMock(return_value="audit-1")
            evidence.envelope = AsyncMock(return_value={"status": "cancelled"})
            browser.close_session = AsyncMock(return_value=True)
            result = await browser_routes.cancel_task("task-3", REQUEST, DB)
        self.assertEqual(result["status"], "cancelled")
        browser.close_session.assert_awaited_once_with("session-3")

    async def test_verify_delegates_to_public_verification(self):
        payload = browser_routes.VerifyRequest(
            session_token="session-4", verification={"expected_text": "ok"}, task_id="task-4"
        )
        with patch.object(browser_routes, "UWAIEService") as uwaie_cls:
            uwaie_cls.return_value.verify = AsyncMock(return_value={
                "verified": True, "envelope": {"status": "completed"},
            })
            result = await browser_routes.verify(payload, REQUEST, DB)
        self.assertTrue(result["verified"])

    async def test_invalid_task_returns_bad_request(self):
        payload = browser_routes.TaskRequest(
            task_id="task-bad",
            steps=[{"action": "navigate", "target": "https://example.com"}],
            session_token="session-5",
        )
        with patch.object(browser_routes.settings, "browser_task_worker_backend", "loop"), \
             patch.object(browser_routes, "BrowserEvidenceService") as evidence_cls:
            evidence_cls.return_value.start_run = AsyncMock(
                side_effect=BrowserEvidenceError("invalid actor type")
            )
            with self.assertRaises(Exception) as raised:
                await browser_routes.create_task(payload, REQUEST, DB)
        self.assertEqual(getattr(raised.exception, "status_code", None), 400)


if __name__ == "__main__":
    unittest.main()
