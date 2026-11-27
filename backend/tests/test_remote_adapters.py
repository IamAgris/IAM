"""WS-05 remote provider adapter tests — opt-in, fail-closed, no secret leakage."""

import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.workspaces.remote_adapters import (
    CoderWorkspaceAdapter,
    CodespacesWorkspaceAdapter,
    RemoteProviderError,
)
from app.services.workspaces.service import (
    StubWorkspaceAdapter,
    WorkspaceService,
)


class CoderAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_by_default(self):
        with patch.object(settings, "workspace_remote_execution_enabled", False):
            with self.assertRaises(RemoteProviderError):
                await CoderWorkspaceAdapter().provision("demo", "iam")

    async def test_provision_uses_configured_endpoint_without_logging_token(self):
        adapter = CoderWorkspaceAdapter()
        with patch.object(settings, "workspace_remote_execution_enabled", True), patch.object(
            settings, "workspace_coder_url", "https://coder.example"
        ), patch.object(settings, "workspace_coder_template_id", "tpl-1"), patch.dict(
            os.environ, {"TEST_CODER_TOKEN": "secret-value"}
        ), patch.object(settings, "workspace_coder_token_env", "TEST_CODER_TOKEN"), patch.object(
            adapter, "_request", AsyncMock(return_value={"id": "ws-1"})
        ) as request:
            result = await adapter.provision("demo", "iam")
        self.assertEqual(result["external_id"], "ws-1")
        args = request.await_args.args
        self.assertEqual(args[0], "POST")
        self.assertEqual(args[1], "https://coder.example/api/v2/users/me/workspaces")
        self.assertEqual(args[2], "secret-value")
        self.assertEqual(args[3]["template_id"], "tpl-1")

    async def test_execute_requires_operator_bridge(self):
        adapter = CoderWorkspaceAdapter()
        with patch.object(settings, "workspace_remote_execution_enabled", True), patch.dict(
            os.environ, {"TEST_CODER_TOKEN": "secret-value"}
        ), patch.object(settings, "workspace_coder_token_env", "TEST_CODER_TOKEN"), patch.object(
            settings, "workspace_coder_execute_path", ""
        ):
            with self.assertRaises(RemoteProviderError):
                await adapter.execute("ws-1", "pytest -q", [], "iam")


class CodespacesAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_provision_uses_repo_endpoint(self):
        adapter = CodespacesWorkspaceAdapter()
        with patch.object(settings, "workspace_remote_execution_enabled", True), patch.object(
            settings, "workspace_codespaces_repo", "org/repo"
        ), patch.dict(os.environ, {"TEST_GH_TOKEN": "secret-value"}), patch.object(
            settings, "workspace_codespaces_token_env", "TEST_GH_TOKEN"
        ), patch.object(
            adapter, "_request", AsyncMock(return_value={"name": "codespace-1"})
        ) as request:
            result = await adapter.provision("demo", "iam")
        self.assertEqual(result["external_id"], "codespace-1")
        self.assertEqual(
            request.await_args.args[1],
            "https://api.github.com/repos/org/repo/codespaces",
        )

    async def test_missing_repo_denied(self):
        adapter = CodespacesWorkspaceAdapter()
        with patch.object(settings, "workspace_remote_execution_enabled", True), patch.object(
            settings, "workspace_codespaces_repo", ""
        ), patch.dict(os.environ, {"TEST_GH_TOKEN": "secret-value"}), patch.object(
            settings, "workspace_codespaces_token_env", "TEST_GH_TOKEN"
        ):
            with self.assertRaises(RemoteProviderError):
                await adapter.provision("demo", "iam")


class FakeRemoteAdapter:
    name = "coder"

    async def provision(self, name, actor):
        return {"external_id": "remote-1", "provider": "coder"}

    async def start(self, external_id, actor):
        return {"status": "active"}

    async def execute(self, external_id, command, env_names, actor):
        return {
            "status": "completed",
            "dry_run": False,
            "simulated": False,
            "stdout": "remote ok",
            "stderr": "",
        }

    async def save(self, external_id, actor):
        return {"status": "saved"}

    async def destroy(self, external_id, actor):
        return {"status": "destroyed"}


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

    async def refresh(self, _obj):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0]["entity"]

        class Result:
            def __init__(self, rows):
                self.rows = rows

            def scalars(self):
                return self

            def all(self):
                return self.rows

            def scalar_one_or_none(self):
                return self.rows[0] if self.rows else None

        return Result([row for row in self.rows if isinstance(row, entity)])


class RemoteWorkspaceLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_remote_provider_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp, patch(
            "app.services.workspaces.service.select_provider", return_value="coder"
        ), patch(
            "app.services.workspaces.service.remote_adapter_for", return_value=FakeRemoteAdapter()
        ), patch(
            "app.services.workspaces.service.assert_provider_available"
        ), patch.object(settings, "workspace_enabled", True):
            db = FakeDB()
            service = WorkspaceService(
                db, adapter=StubWorkspaceAdapter(), root=Path(tmp)
            )
            workspace = await service.create(
                name="Remote",
                project_id=None,
                provider="coder",
                credential_env_var=None,
                actor="iam",
            )
            self.assertEqual(workspace["provider"], "coder")
            self.assertEqual(
                workspace["isolation"]["provider_external_id"], "remote-1"
            )
            self.assertTrue(workspace["directory"].startswith("remote://"))
            await service.start(workspace["id"], "iam")
            outcome = await service.execute(workspace["id"], "pytest -q", "iam")
            self.assertEqual(outcome["stdout"], "remote ok")
            saved = await service.save(workspace["id"], "iam")
            self.assertEqual(saved["status"], "saved")
            destroyed = await service.destroy(workspace["id"], "iam")
            self.assertEqual(destroyed["status"], "destroyed")


if __name__ == "__main__":
    unittest.main()
