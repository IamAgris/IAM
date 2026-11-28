"""WH-03…WH-09 enforcement tests: labs, validation, audit, P2P exclusion."""

import asyncio
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.config import settings
from app.models.security import AuditEvent
from app.models.security_labs import SecurityWorkSession
from app.services.p2p_transport import P2PTransport
from app.services.whitehat_labs import WhiteHatLabService
from app.services.whitehat_policy import (
    STUDY_POLICY,
    WhiteHatPolicyError,
    build_security_audit,
    ensure_learning_only,
    ensure_p2p_shareable,
)

AUTHORITY = {
    "authorized": True,
    "authorization_id": str(uuid.uuid4()),
    "signer_id": "creator-signer",
    "target": "lab.example.internal",
    "operation": "read",
    "expires_at": "2026-11-26T00:00:00+00:00",
}


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

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


class FakePolicy:
    def __init__(self, _db):
        pass

    async def verify(self, target, operation="read", **_kwargs):
        return dict(AUTHORITY)


class FakeWorkspaces:
    def __init__(self, outcome="completed"):
        self.outcome = outcome
        self.destroyed = []

    async def create(self, **_kwargs):
        return {"id": str(uuid.uuid4())}

    async def start(self, workspace_id, actor):
        return {"id": workspace_id, "status": "active"}

    async def execute(self, workspace_id, command, actor):
        return {"status": self.outcome, "stdout": "ok", "stderr": ""}

    async def destroy(self, workspace_id, actor):
        self.destroyed.append(workspace_id)
        return {"id": workspace_id, "status": "destroyed"}


class PolicyTests(unittest.TestCase):
    def test_study_policy_never_grants_capability(self):
        self.assertTrue(STUDY_POLICY["learning_only"])
        self.assertFalse(STUDY_POLICY["execution_allowed"])
        self.assertFalse(STUDY_POLICY["capability_granted"])

    def test_learning_only_rejects_executable_fields(self):
        with self.assertRaises(WhiteHatPolicyError):
            ensure_learning_only({"notes": "study", "script": "print('x')"})
        with self.assertRaises(WhiteHatPolicyError):
            ensure_learning_only({"summary": "reverse-shell details"})

    def test_p2p_topic_and_payload_filter(self):
        ensure_p2p_shareable("report", {"summary": "defensive finding"})
        with self.assertRaises(WhiteHatPolicyError):
            ensure_p2p_shareable("offensive_tool", {"name": "x"})
        with self.assertRaises(WhiteHatPolicyError):
            ensure_p2p_shareable("research", {"payload": "executable bytes"})

    def test_security_audit_schema(self):
        audit = build_security_audit(
            action="scan",
            actor="iam",
            target="lab.example.internal",
            scope={},
            authority=AUTHORITY,
            tool_calls=["workspace.execute"],
            approval={"authorization_id": AUTHORITY["authorization_id"]},
            changes={},
        )
        for key in ("target", "scope", "authority", "tool_calls", "approval", "changes"):
            self.assertIn(key, audit)

    def test_p2p_transport_rejects_offensive_payload(self):
        transport = P2PTransport()
        with self.assertRaises(WhiteHatPolicyError):
            asyncio.run(transport.broadcast("offensive_tool", {"script": "x"}))
        result = asyncio.run(
            transport.broadcast("report", {"summary": "defensive finding"})
        )
        self.assertIn("envelope", result)


class WhiteHatLabTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = FakeDB()
        self.workspaces = FakeWorkspaces()
        self.patchers = [
            patch("app.services.whitehat_labs.AuthorisedTargetPolicy", FakePolicy),
            patch(
                "app.services.whitehat_labs.WorkspaceService",
                lambda _db: self.workspaces,
            ),
        ]
        for patcher in self.patchers:
            patcher.start()
        self.addCleanup(lambda: [p.stop() for p in self.patchers])

    async def test_create_start_destroy_lab(self):
        service = WhiteHatLabService(self.db)
        session = await service.create_lab("lab.example.internal", "iam")
        self.assertEqual(session["kind"], "simulation_lab")
        self.assertEqual(session["authorization_id"], AUTHORITY["authorization_id"])
        started = await service.start_lab(session["id"], "iam")
        self.assertEqual(started["status"], "running")
        destroyed = await service.destroy_session(session["id"], "iam")
        self.assertEqual(destroyed["status"], "destroyed")
        self.assertTrue(self.workspaces.destroyed)
        audit = [row for row in self.db.rows if isinstance(row, AuditEvent)]
        self.assertTrue(any(row.event_type == "security_work_session" for row in audit))

    async def test_remediation_verified_only_after_validation(self):
        with patch.object(settings, "workspace_enabled", True):
            service = WhiteHatLabService(self.db)
            result = await service.validate_remediation(
                "lab.example.internal",
                "finding-1",
                "add a permission check",
                "pytest -q",
                "iam",
            )
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["validation"]["status"], "completed")

    async def test_remediation_not_verified_when_execution_disabled(self):
        with patch.object(settings, "workspace_enabled", False):
            service = WhiteHatLabService(self.db)
            result = await service.validate_remediation(
                "lab.example.internal",
                "finding-1",
                "add a permission check",
                "pytest -q",
                "iam",
            )
        self.assertEqual(result["status"], "failed")
        self.assertIn("disabled", result["validation"]["reason"])

    async def test_expired_sessions_cleanup(self):
        service = WhiteHatLabService(self.db)
        session = await service.create_lab("lab.example.internal", "iam")
        row = next(
            item
            for item in self.db.rows
            if isinstance(item, SecurityWorkSession)
            and str(item.id) == session["id"]
        )
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.assertEqual(await service.cleanup_expired(), 1)
        self.assertEqual(row.status, "expired")


if __name__ == "__main__":
    unittest.main()
