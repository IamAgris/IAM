"""Phase 9 conformance: protocol version, UWAIE lifecycle, presence and accounts."""

import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.models.internetaccess import InternetSession, OnlineAccount
from app.models.security import AuditEvent
from app.models.socialintel import SocialPresence
from app.models.uwaie import WebsiteWorkflow
from app.services.browser_service import BrowserService
from app.services.internetaccess_service import InternetAccessService
from app.services.socialpresence_service import SocialPresenceError, SocialPresenceService
from app.services.uwaie_service import UWAIEError, UWAIEService


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
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    def add(self, obj):
        if obj not in self.rows:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.rows.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])

    async def refresh(self, _obj):
        return None

    async def _log_event(self, *_args, **_kwargs):
        return None


def approvals(authorized=True):
    class Approvals:
        def __init__(self, _db):
            pass

        async def check_authorization(self, _action, requested_level="3", target_ref=None):
            if not authorized:
                return {"authorized": False, "reason": "unsigned"}
            return {
                "authorized": True,
                "authorization_id": str(uuid.uuid4()),
                "signer_id": "creator-signer",
            }

    return Approvals


class ProtocolTests(unittest.TestCase):
    def test_incompatible_version_returns_426(self):
        client = TestClient(app)
        response = client.get(
            "/api/v1/knowledge", headers={"X-IAM-Protocol-Version": "99"}
        )
        self.assertEqual(response.status_code, 426)
        self.assertEqual(response.json()["required_version"], settings.iam_protocol_version)

    def test_protocol_endpoint_advertises_version(self):
        with patch.object(settings, "auth_enabled", False):
            response = TestClient(app).get("/api/v1/auth/protocol")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], settings.iam_protocol_version)


class UWAIELifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_approval_reuse_and_handover(self):
        workflow = WebsiteWorkflow(
            id=uuid.uuid4(),
            name="demo",
            url_pattern="https://example.com",
            steps=[{"action": "navigate", "target": "https://example.com"}],
            verification={"expected_url": "https://example.com"},
            source_actor="iam",
            is_approved=False,
        )
        db = FakeDB([workflow])
        service = UWAIEService(db)
        with patch("app.services.uwaie_service.CreatorApprovalService", approvals(False)):
            with self.assertRaises(UWAIEError):
                await service.approve_workflow(str(workflow.id), "", "iam")
        with patch("app.services.uwaie_service.CreatorApprovalService", approvals()):
            await service.approve_workflow(str(workflow.id), "", "iam")
        self.assertTrue(workflow.is_approved)
        with patch.object(service, "execute", AsyncMock(return_value={"status": "ok"})):
            result = await service.reuse_workflow(
                str(workflow.id), "https://example.com/start", None, "iam"
            )
        self.assertEqual(result["status"], "ok")
        handover = await service.request_handover(
            "https://example.com/login", "credentials required", "iam"
        )
        self.assertEqual(handover["status"], "pending_human")
        self.assertFalse(handover["autonomous_action_taken"])
        self.assertTrue(any(row.event_type == "uwaie_human_handover_requested" for row in db.rows if isinstance(row, AuditEvent)))


class PresenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_register_and_verify_presence(self):
        db = FakeDB()
        service = SocialPresenceService(db)
        with patch("app.services.socialpresence_service.CreatorApprovalService", approvals(False)):
            with self.assertRaises(SocialPresenceError):
                await service.register(
                    platform="social", handle="@iam", profile_url="https://social.example/iam",
                    owner_entity="Aura Holdings", approval_id="fake", actor="iam",
                )
        with patch("app.services.socialpresence_service.CreatorApprovalService", approvals()):
            row = await service.register(
                platform="social", handle="@iam", profile_url="https://social.example/iam",
                owner_entity="Aura Holdings", approval_id="r1", actor="iam",
            )
            verified = await service.verify(row["id"], "", "iam")
        self.assertFalse(row["verified"])
        self.assertTrue(verified["verified"])
        self.assertEqual(len(await service.list(verified_only=True)), 1)


class AccountLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_rotate_and_close_account(self):
        account = OnlineAccount(
            id=uuid.uuid4(),
            platform="example",
            account_identifier="acct-1",
            account_type="service",
            is_authorised=True,
            credential_reference="OLD_TOKEN",
        )
        service = InternetAccessService(FakeDB([account]))
        with patch("app.services.internetaccess_service.CreatorApprovalService", approvals()):
            rotated = await service.rotate_account_credential(
                str(account.id), "NEW_TOKEN", "iam"
            )
            closed = await service.close_account(str(account.id), "iam")
        self.assertEqual(rotated["credential_reference"], "NEW_TOKEN")
        self.assertFalse(closed["is_authorised"])
        self.assertEqual(len(await service.list_accounts()), 1)

        with patch("app.services.internetaccess_service.CreatorApprovalService", approvals()):
            with self.assertRaises(PermissionError):
                await service.rotate_account_credential(
                    str(account.id), "literal-secret-value", "iam"
                )


class BrowserAutomationTests(unittest.IsolatedAsyncioTestCase):
    async def test_engine_allowlist_and_transfer_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(settings, "uwai_upload_root", tmp):
                browser = BrowserService(engine="firefox")
                self.assertEqual(browser.engine, "firefox")
                with self.assertRaises(ValueError):
                    BrowserService(engine="unknown")
                safe = browser._safe_transfer_path("../../etc/passwd")
                self.assertEqual(safe.name, "passwd")
                self.assertIn(browser.transfer_root, safe.parents)

    async def test_upload_uses_bounded_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(settings, "uwai_upload_root", tmp):
                browser = BrowserService()
                Path(browser.transfer_root / "a.txt").write_text("data", encoding="utf-8")
                page = type(
                    "Page",
                    (),
                    {"set_input_files": AsyncMock(), "click": AsyncMock()},
                )()
                result = await browser.interact(
                    "upload", "#file", value="a.txt", page=page
                )
        self.assertTrue(result["success"])
        self.assertEqual(page.set_input_files.await_args.args[1], str(browser.transfer_root / "a.txt"))

    async def test_upload_permission_gate_and_recovery(self):
        session = InternetSession(session_token="t-1", purpose="test", is_active=True)
        db = FakeDB([session])
        service = UWAIEService(db)
        with patch.object(
            service.access,
            "check_permission",
            AsyncMock(return_value={"permitted": False, "reason": "approval required"}),
        ):
            with self.assertRaises(UWAIEError):
                await service._check_steps([{"action": "upload", "target": "#f", "value": "a.txt"}])

        with patch(
            "app.services.uwaie_service.browser_service.interact",
            AsyncMock(return_value={"success": False, "error": "selector changed"}),
        ), patch.object(
            service,
            "inspect",
            AsyncMock(return_value={"url": "https://example.com", "forms": 1}),
        ):
            result = await service.execute(
                steps=[{"action": "navigate", "target": "https://example.com"}],
                verification={},
                session_token="t-1",
                actor="iam",
            )
        self.assertFalse(result["verified"])
        self.assertIn("url", result["recovery"])
        self.assertTrue(any(row.event_type == "uwaie_recovery" for row in db.rows if isinstance(row, AuditEvent)))


if __name__ == "__main__":
    unittest.main()
