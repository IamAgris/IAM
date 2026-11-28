"""WS-01/WS-02 workspace manager and isolation tests."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.models.security import AuditEvent
from app.models.workspaces import WorkspaceEnvironment
from app.services.workspaces.service import (
    DockerWorkspaceAdapter,
    StubWorkspaceAdapter,
    WorkspaceError,
    WorkspaceIsolation,
    WorkspaceService,
    validate_command,
    validate_credential_env_var,
    validate_isolation,
    workspace_digest,
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
    def __init__(self):
        self.rows = []

    def add(self, obj):
        if obj not in self.rows:
            if getattr(obj, "id", None) is None:
                import uuid

                obj.id = uuid.uuid4()
            self.rows.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def refresh(self, _obj):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]
        return FakeResult([row for row in self.rows if isinstance(row, entity)])


class IsolationTests(unittest.TestCase):
    def test_default_isolation_is_conservative(self):
        isolation = WorkspaceIsolation()
        validate_isolation(isolation.as_dict())
        self.assertFalse(isolation.core_access)
        self.assertEqual(isolation.network, "none")

    def test_core_access_and_network_denied(self):
        with self.assertRaises(WorkspaceError):
            validate_isolation({"core_access": True})
        with self.assertRaises(WorkspaceError):
            validate_isolation({"network": "bridge"})
        with self.assertRaises(WorkspaceError):
            validate_isolation({"non_root": False})

    def test_offensive_commands_denied(self):
        for command in ("exploit_target", "sudo apt-get install x", "rm -rf /"):
            with self.assertRaises(WorkspaceError, msg=command):
                validate_command(command)
        self.assertEqual(validate_command("pytest -q"), "pytest -q")

    def test_credential_names_only(self):
        self.assertEqual(validate_credential_env_var("GITHUB_TOKEN"), "GITHUB_TOKEN")
        self.assertIsNone(validate_credential_env_var(None))
        for bad in ("IAM_API_KEY", "CREATOR_GATEWAY_SECRET", "POSTGRES_PASSWORD", "iam_key"):
            with self.assertRaises(WorkspaceError, msg=bad):
                validate_credential_env_var(bad)

    def test_docker_command_hardening(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = DockerWorkspaceAdapter().command(
                Path(tmp), "pytest -q", WorkspaceIsolation().as_dict(), "GITHUB_TOKEN"
            )
        self.assertEqual(command[command.index("--network") + 1], "none")
        self.assertIn("--cap-drop", command)
        self.assertIn("no-new-privileges", command)
        self.assertIn("65534:65534", command)
        self.assertTrue(any(arg.endswith(":/workspace:rw") for arg in command))
        self.assertFalse(any("/app" in arg or "/opt/iam" in arg for arg in command))
        self.assertIn("GITHUB_TOKEN", command)

    def test_digest_tracks_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.py").write_text("one", encoding="utf-8")
            first = workspace_digest(root)
            (root / "a.py").write_text("two", encoding="utf-8")
            self.assertNotEqual(first, workspace_digest(root))


class WorkspaceLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_start_execute_save_destroy(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = FakeDB()
            service = WorkspaceService(db, adapter=StubWorkspaceAdapter(), root=Path(tmp))
            created = await service.create(
                name="Demo",
                project_id=None,
                provider="local",
                credential_env_var="GITHUB_TOKEN",
                actor="iam",
            )
            self.assertEqual(created["status"], "provisioning")
            self.assertEqual(created["isolation"]["core_access"], False)

            started = await service.start(created["id"], "iam")
            self.assertEqual(started["status"], "active")

            with patch.object(settings, "workspace_enabled", True):
                outcome = await service.execute(created["id"], "pytest -q", "iam")
            self.assertTrue(outcome["simulated"])
            self.assertTrue(outcome["dry_run"])

            saved = await service.save(created["id"], "iam")
            self.assertEqual(saved["status"], "saved")
            self.assertTrue(saved["isolation"]["checksum"])

            destroyed = await service.destroy(created["id"], "iam")
            self.assertEqual(destroyed["status"], "destroyed")
            self.assertFalse(Path(destroyed["directory"]).exists())

            audit_events = [row for row in db.rows if isinstance(row, AuditEvent)]
            self.assertTrue(
                any(row.event_type == "workspace_created" for row in audit_events)
            )
            self.assertTrue(any(row.event_type == "workspace_log" for row in audit_events))

    async def test_execute_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            settings, "workspace_enabled", False
        ):
            db = FakeDB()
            service = WorkspaceService(db, adapter=StubWorkspaceAdapter(), root=Path(tmp))
            created = await service.create(
                name="Demo", project_id=None, provider="local",
                credential_env_var=None, actor="iam",
            )
            await service.start(created["id"], "iam")
            with self.assertRaises(WorkspaceError):
                await service.execute(created["id"], "echo hi", "iam")

    async def test_unsupported_provider_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = WorkspaceService(FakeDB(), root=Path(tmp))
            with self.assertRaises(WorkspaceError):
                await service.create(
                    name="Demo", project_id=None, provider="unknown",
                    credential_env_var=None, actor="iam",
                )


if __name__ == "__main__":
    unittest.main()
