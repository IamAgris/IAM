"""Scheduled post-deploy monitoring is opt-in and never self-authorizes rollback."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.ai_research import post_deploy
from app.workers.arq_model_catalog import run_post_deploy_checks


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


def fake_service(baseline=0.8):
    return SimpleNamespace(
        registry=SimpleNamespace(
            get=lambda _m, _v: SimpleNamespace(benchmark_score=baseline)
        ),
        rollback=AsyncMock(return_value={"status": "rolled_back"}),
    )


class PostDeployMonitorTests(unittest.IsolatedAsyncioTestCase):
    async def test_awaitable_evaluator_is_supported(self):
        async def evaluate(_model: str) -> float:
            return 0.4

        with (
            patch.object(settings, "post_deploy_monitor_enabled", True),
            patch.object(settings, "post_deploy_auto_rollback_enabled", False),
            patch.object(post_deploy, "ModelReleaseService", return_value=fake_service()),
        ):
            result = await post_deploy.check_regression(
                FakeDB(), "local-qwen-3b", "v1", evaluate=evaluate
            )
        self.assertTrue(result.regressed)
        self.assertEqual(result.action, "approval_required")

    async def test_monitor_is_noop_when_disabled(self):
        with patch.object(settings, "post_deploy_monitor_enabled", False):
            result = await run_post_deploy_checks({})
        self.assertEqual(result, {"enabled": False, "checked": 0})


if __name__ == "__main__":
    unittest.main()
