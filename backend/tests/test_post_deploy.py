"""Post-deploy regression checks never self-authorize a rollback."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.ai_research import post_deploy
from app.services.ai_research.base import ResearchError


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


def service(baseline=0.8):
    return SimpleNamespace(
        registry=SimpleNamespace(
            get=lambda _model, _version: SimpleNamespace(benchmark_score=baseline)
        ),
        rollback=AsyncMock(return_value={"status": "rolled_back"}),
    )


class PostDeployTests(unittest.IsolatedAsyncioTestCase):
    async def test_regression_requires_approval_by_default(self):
        with (
            patch.object(settings, "post_deploy_monitor_enabled", True),
            patch.object(settings, "post_deploy_auto_rollback_enabled", False),
            patch.object(post_deploy, "ModelReleaseService", return_value=service()),
        ):
            result = await post_deploy.check_regression(
                FakeDB(), "local-qwen-coder-3b", "v1", evaluate=lambda _m: 0.4
            )
        self.assertTrue(result.regressed)
        self.assertEqual(result.action, "approval_required")
        self.assertIn("score fell", result.reason)

    async def test_no_regression_is_observed(self):
        with (
            patch.object(settings, "post_deploy_monitor_enabled", True),
            patch.object(post_deploy, "ModelReleaseService", return_value=service()),
        ):
            result = await post_deploy.check_regression(
                FakeDB(), "local-qwen-coder-3b", "v1", evaluate=lambda _m: 0.79
            )
        self.assertFalse(result.regressed)
        self.assertEqual(result.action, "observe")

    async def test_auto_rollback_uses_previous_deployed_version(self):
        fake = service()
        with (
            patch.object(settings, "post_deploy_monitor_enabled", True),
            patch.object(settings, "post_deploy_auto_rollback_enabled", True),
            patch.object(
                post_deploy.serving_model,
                "current",
                return_value=SimpleNamespace(previous_version="v0"),
            ),
            patch.object(post_deploy, "ModelReleaseService", return_value=fake),
        ):
            result = await post_deploy.check_regression(
                FakeDB(), "local-qwen-coder-3b", "v1", evaluate=lambda _m: 0.4
            )
        self.assertEqual(result.action, "rolled_back")
        fake.rollback.assert_awaited_once()
        self.assertEqual(fake.rollback.await_args.args[1], "v0")

    async def test_unknown_version_fails_closed(self):
        def missing(_model, _version):
            raise ResearchError("unknown model version")

        with patch.object(
            post_deploy,
            "ModelReleaseService",
            return_value=SimpleNamespace(
                registry=SimpleNamespace(get=missing), rollback=AsyncMock()
            ),
        ):
            with self.assertRaises(post_deploy.ModelReleaseError):
                await post_deploy.check_regression(
                    FakeDB(), "local-qwen-coder-3b", "v9", evaluate=lambda _m: 0.8
                )


if __name__ == "__main__":
    unittest.main()
