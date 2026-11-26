"""WS-03/WS-05/WS-06 tests: scoped credentials and provider continuity."""

import os
import tempfile
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from app.core.config import settings
from app.models.security import AuditEvent
from app.models.workspace_credentials import WorkspaceCredential
from app.services.workspaces.providers import (
    assert_provider_available,
    provider_statuses,
    select_provider,
)
from app.services.workspaces.service import (
    StubWorkspaceAdapter,
    WorkspaceError,
    WorkspaceService,
    check_command_hosts,
    validate_credential_scopes,
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
                obj.id = uuid.uuid4()
            if getattr(obj, "issued_at", None) is None:
                obj.issued_at = datetime.now(timezone.utc)
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


class ProviderTests(unittest.TestCase):
    def test_local_is_always_available(self):
        with patch.object(settings, "workspace_providers", "coder,codespaces"):
            statuses = provider_statuses()
        self.assertTrue(any(status.name == "local" and status.available for status in statuses))

    def test_unconfigured_online_provider_falls_back_to_local(self):
        with patch.object(settings, "workspace_providers", "local,coder"), patch.object(
            settings, "workspace_coder_url", ""
        ):
            self.assertEqual(select_provider("coder"), "local")
            with self.assertRaises(WorkspaceError):
                assert_provider_available("coder")

    def test_configured_online_provider_is_selectable(self):
        with patch.dict(os.environ, {"TEST_CODER_TOKEN": "placeholder"}), patch.object(
            settings, "workspace_providers", "local,coder"
        ), patch.object(settings, "workspace_coder_url", "https://coder.example"), patch.object(
            settings, "workspace_coder_token_env", "TEST_CODER_TOKEN"
        ), patch.object(settings, "workspace_remote_execution_enabled", True):
            self.assertTrue(assert_provider_available("coder").available)
            self.assertEqual(select_provider("coder"), "coder")


class ScopeTests(unittest.TestCase):
    def test_wildcard_hosts_rejected(self):
        with self.assertRaises(WorkspaceError):
            validate_credential_scopes({"allowed_hosts": ["*"]})

    def test_command_host_gate(self):
        credential = type(
            "Credential",
            (),
            {"scopes": {"allowed_hosts": ["github.com"]}, "secret_env_var": "GITHUB_TOKEN"},
        )()
        check_command_hosts("git clone https://github.com/org/repo", [credential])
        with self.assertRaises(WorkspaceError):
            check_command_hosts("curl https://evil.example", [credential])


class CredentialLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_issue_use_revoke(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(
            settings, "workspace_enabled", True
        ):
            db = FakeDB()
            service = WorkspaceService(db, adapter=StubWorkspaceAdapter(), root=Path(tmp))
            workspace = await service.create(
                name="Demo", project_id=None, provider="local",
                credential_env_var=None, actor="iam",
            )
            await service.start(workspace["id"], "iam")

            credential = await service.issue_credential(
                workspace["id"],
                purpose="git",
                secret_env_var="GITHUB_TOKEN",
                scopes={"allowed_hosts": ["github.com"]},
                ttl_seconds=600,
                actor="iam",
            )
            self.assertEqual(credential["secret_env_var"], "GITHUB_TOKEN")
            self.assertFalse(any("token" in str(v).lower() for v in credential.values() if v != "GITHUB_TOKEN"))
            self.assertEqual(len(await service.list_credentials(workspace["id"])), 1)

            outcome = await service.execute(
                workspace["id"], "git clone https://github.com/org/repo", "iam"
            )
            self.assertTrue(outcome["simulated"])

            revoked = await service.revoke_credential(
                workspace["id"], credential["id"], "iam"
            )
            self.assertFalse(revoked["is_active"])
            with self.assertRaises(WorkspaceError):
                await service.execute(
                    workspace["id"], "git clone https://github.com/org/repo", "iam"
                )

            audit = [row for row in db.rows if isinstance(row, AuditEvent)]
            self.assertTrue(
                any(row.event_type == "workspace_credential_issued" for row in audit)
            )
            self.assertTrue(
                any(row.event_type == "workspace_credential_revoked" for row in audit)
            )

    async def test_expired_credential_not_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = FakeDB()
            service = WorkspaceService(db, adapter=StubWorkspaceAdapter(), root=Path(tmp))
            workspace = await service.create(
                name="Demo", project_id=None, provider="local",
                credential_env_var=None, actor="iam",
            )
            credential = WorkspaceCredential(
                workspace_id=uuid.UUID(workspace["id"]),
                purpose="git",
                secret_env_var="GITHUB_TOKEN",
                scopes={"allowed_hosts": ["github.com"]},
                expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            )
            db.add(credential)
            self.assertEqual(await service._active_credentials(workspace["id"]), [])


if __name__ == "__main__":
    unittest.main()
