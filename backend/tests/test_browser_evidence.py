"""Doc 29 WP-03 tests: browser task envelopes, evidence and attribution."""

import base64
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.models.web_knowledge import BrowserAudit, BrowserEvidence, BrowserTaskRun
from app.services.autonomous_web_task_service import AutonomousWebTaskService
from app.services.browser_evidence_service import (
    BrowserEvidenceError,
    BrowserEvidenceService,
    build_envelope,
    redact,
)


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
    """Minimal async DB double matching the repo's existing test convention."""

    def __init__(self):
        self.rows = []

    def add(self, obj):
        if obj not in self.rows:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()
            self.rows.append(obj)

    async def delete(self, obj):
        if obj in self.rows:
            self.rows.remove(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        rows = [row for row in self.rows if isinstance(row, entity)]
        where = getattr(statement, "whereclause", None)
        if where is not None and hasattr(where, "left") and hasattr(where.left, "key"):
            key = where.left.key
            value = getattr(where.right, "value", None)
            rows = [row for row in rows if getattr(row, key, None) == value]
        return FakeResult(rows)


class RedactionTests(unittest.TestCase):
    def test_secret_keys_and_bearer_tokens_are_removed(self):
        payload = {
            "password": "hunter2",
            "nested": {"api_key": "abc", "note": "Authorization: Bearer abc123"},
            "safe": "public value",
        }
        cleaned = redact(payload)
        self.assertEqual(cleaned["password"], "[REDACTED]")
        self.assertEqual(cleaned["nested"]["api_key"], "[REDACTED]")
        self.assertNotIn("abc123", cleaned["nested"]["note"])
        self.assertEqual(cleaned["safe"], "public value")

    def test_envelope_rejects_invalid_status_and_actor(self):
        with self.assertRaises(BrowserEvidenceError):
            build_envelope("t", status="claimed_success")
        with self.assertRaises(BrowserEvidenceError):
            build_envelope("t", actor_type="system")


class EvidenceServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = BrowserEvidenceService(self.db)
        self.tempdir = tempfile.TemporaryDirectory()
        self.settings_patch = patch.object(
            settings, "browser_evidence_dir", self.tempdir.name
        )
        self.settings_patch.start()
        await self.service.start_run(
            task_id="task-1", actor="iam", actor_type="agent",
            permission_scope="browse_public", session_id="session-1",
            mode="headless", engine="chromium",
        )

    async def asyncTearDown(self):
        self.settings_patch.stop()
        self.tempdir.cleanup()

    async def test_state_machine_blocks_false_success(self):
        with self.assertRaises(BrowserEvidenceError):
            await self.service.set_state("task-1", "completed")
        await self.service.set_state("task-1", "running")
        await self.service.set_state("task-1", "verifying")
        run = await self.service.set_state("task-1", "completed")
        self.assertEqual(run["state"], "completed")
        self.assertIsNotNone(run["started_at"])
        self.assertIsNotNone(run["finished_at"])
        with self.assertRaises(BrowserEvidenceError):
            await self.service.set_state("task-1", "running")

    async def test_evidence_package_is_hashed_redacted_and_referenced(self):
        image = b"fake-png-bytes"
        evidence_id = await self.service.record_evidence(
            "task-1",
            url="https://example.com",
            screenshot_b64=base64.b64encode(image).decode("ascii"),
            excerpt="Authorization: Bearer supersecret public text",
            source_metadata={"api_token": "abc", "title": "Example"},
            session_id="session-1",
        )
        rows = [row for row in self.db.rows if isinstance(row, BrowserEvidence)]
        self.assertEqual(len(rows), 1)
        self.assertNotIn("supersecret", rows[0].excerpt)
        self.assertNotIn("abc", str(rows[0].source_metadata))
        self.assertTrue(Path(rows[0].screenshot_ref).read_bytes() == image)
        self.assertEqual(len(rows[0].sha256), 64)
        envelope = await self.service.envelope("task-1")
        self.assertEqual(envelope["task_id"], "task-1")
        self.assertEqual(envelope["actor_type"], "agent")
        self.assertEqual(envelope["permission_scope"], "browse_public")
        self.assertEqual(envelope["evidence_refs"], [evidence_id])

    async def test_audit_is_attributed_and_rejects_unknown_actor(self):
        await self.service.append_audit(
            "task-1", actor="creator", actor_type="creator",
            action="approval.granted", target="task-1",
            outcome={"password": "should-not-persist", "approved": True},
        )
        rows = [row for row in self.db.rows if isinstance(row, BrowserAudit)]
        self.assertEqual(rows[0].actor, "creator")
        self.assertEqual(rows[0].actor_type, "creator")
        self.assertEqual(rows[0].outcome["password"], "[REDACTED]")
        with self.assertRaises(BrowserEvidenceError):
            await self.service.append_audit(
                "task-1", actor="x", actor_type="system", action="bad"
            )


class DeadlineRetryAndRetentionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.service = BrowserEvidenceService(self.db)
        self.tempdir = tempfile.TemporaryDirectory()
        self.settings_patch = patch.object(
            settings, "browser_evidence_dir", self.tempdir.name
        )
        self.settings_patch.start()

    async def asyncTearDown(self):
        self.settings_patch.stop()
        self.tempdir.cleanup()

    async def test_deadline_is_enforced(self):
        await self.service.start_run(
            task_id="deadline-1", actor="iam",
            deadline=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        self.assertTrue(await self.service.is_expired("deadline-1"))
        await self.service.set_state("deadline-1", "timed_out")

    async def test_retry_count_is_bounded(self):
        await self.service.start_run(task_id="retry-1", actor="iam")
        self.assertEqual(await self.service.increment_retry("retry-1", max_retries=1), 1)
        with self.assertRaises(BrowserEvidenceError):
            await self.service.increment_retry("retry-1", max_retries=1)

    async def test_purge_expired_removes_rows_and_files(self):
        await self.service.start_run(task_id="purge-1", actor="iam")
        await self.service.record_evidence(
            "purge-1",
            screenshot_b64=base64.b64encode(b"image").decode("ascii"),
            excerpt="public",
        )
        row = next(r for r in self.db.rows if isinstance(r, BrowserEvidence))
        row.retention_until = datetime.now(timezone.utc) - timedelta(days=1)
        path = Path(row.screenshot_ref)
        self.assertTrue(path.exists())
        removed = await self.service.purge_expired()
        self.assertEqual(removed, 1)
        self.assertFalse(path.exists())
        self.assertFalse(any(isinstance(r, BrowserEvidence) for r in self.db.rows))


class AutonomousTaskEnvelopeTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_records_an_attributed_run(self):
        db = FakeDB()
        service = AutonomousWebTaskService(db)
        task = await service.create(
            title="Research hosting",
            task_type="research",
            actor="iam",
            actor_type="agent",
            permission_scope="browse_public",
            mode="isolated",
        )
        self.assertEqual(task["task_id"], task["id"])
        self.assertEqual(task["status"], "pending")
        self.assertEqual(task["run_state"], "queued")
        self.assertEqual(task["envelope"]["actor_type"], "agent")
        self.assertEqual(task["actor"], "iam")
        self.assertEqual(task["permission_scope"], "browse_public")
        runs = [row for row in db.rows if isinstance(row, BrowserTaskRun)]
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0].mode, "isolated")
        fetched = await service.get(task["id"])
        self.assertEqual(fetched["task_id"], task["id"])


if __name__ == "__main__":
    unittest.main()
