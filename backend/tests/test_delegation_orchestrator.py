"""OD-51 §4.4: bounded parallel delegation with fail-closed partial results."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.services.delegation import DelegationResult
from app.services.delegation_orchestrator import (
    DelegationTask,
    OrchestrationResult,
    run_parallel,
)


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


def _factory():
    return FakeSession()


def _accepted(model="nvidia-a", finding="checked finding"):
    return DelegationResult(
        "accepted", model, verdict="accept", findings=[finding], authorization_id="signed-1"
    )


class DelegationOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_call_count_limit_denies_before_any_delegate(self):
        mock = AsyncMock(return_value=_accepted())
        with patch("app.services.delegation_orchestrator.get_session_factory", return_value=_factory), \
             patch("app.services.delegation_orchestrator.delegation.run", new=mock), \
             patch("app.services.delegation_orchestrator.settings.iam_delegation_max_calls_per_request", 2):
            result = await run_parallel(
                None, [DelegationTask(f"task {i}") for i in range(3)]
            )
        self.assertIsNotNone(result.denied_reason)
        mock.assert_not_awaited()

    async def test_concurrency_never_exceeds_confirmed_bound(self):
        active = 0
        high_water = 0

        async def work(*args, **kwargs):
            nonlocal active, high_water
            active += 1
            high_water = max(high_water, active)
            await asyncio.sleep(0.01)
            active -= 1
            return _accepted()

        with patch("app.services.delegation_orchestrator.get_session_factory", return_value=_factory), \
             patch("app.services.delegation_orchestrator.delegation.run", new=AsyncMock(side_effect=work)), \
             patch("app.services.delegation_orchestrator.settings.iam_delegation_max_parallel", 2), \
             patch("app.services.delegation_orchestrator.settings.iam_delegation_max_calls_per_request", 4):
            result = await run_parallel(
                None, [DelegationTask(f"task {i}") for i in range(4)]
            )
        self.assertEqual(high_water, 2)
        self.assertEqual(len(result.accepted), 4)

    async def test_timeout_produces_error_not_partial_acceptance(self):
        async def slow(*args, **kwargs):
            await asyncio.sleep(0.05)
            return _accepted()

        with patch("app.services.delegation_orchestrator.get_session_factory", return_value=_factory), \
             patch("app.services.delegation_orchestrator.delegation.run", new=AsyncMock(side_effect=slow)), \
             patch("app.services.delegation_orchestrator.settings.iam_delegation_timeout_seconds", 0.01):
            result = await run_parallel(None, [DelegationTask("slow task")])
        self.assertEqual(result.results[0].status, "error")
        self.assertIn("timed out", result.results[0].reason)
        self.assertIsNone(result.context_message())

    async def test_only_accepted_findings_reach_primary_context(self):
        outcomes = [
            _accepted("nvidia-a", "accepted claim"),
            DelegationResult("rejected", "nvidia-b", reason="IAM rejected"),
        ]
        mock = AsyncMock(side_effect=outcomes)
        with patch("app.services.delegation_orchestrator.get_session_factory", return_value=_factory), \
             patch("app.services.delegation_orchestrator.delegation.run", new=mock):
            result = await run_parallel(
                None, [DelegationTask("one"), DelegationTask("two")]
            )
        context = result.context_message()
        self.assertIn("accepted claim", context)
        self.assertNotIn("rejected", context)
        self.assertEqual(len(result.accepted), 1)

    async def test_local_alias_cannot_be_used_as_delegate(self):
        with patch("app.services.delegation_orchestrator.get_session_factory", return_value=_factory), \
             patch("app.services.delegation_orchestrator.settings.iam_delegation_enabled", True):
            result = await run_parallel(
                None, [DelegationTask("task", model="local-qwen-coder-3b")]
            )
        self.assertEqual(result.results[0].status, "rejected")
        self.assertIn("external specialist", result.results[0].reason)

    async def test_disabled_delegation_fails_closed(self):
        with patch("app.services.delegation_orchestrator.settings.iam_delegation_enabled", False):
            result = await run_parallel(None, [DelegationTask("task")])
        self.assertEqual(result.denied_reason, "delegation disabled")
        self.assertIsNone(result.context_message())

    async def test_serialized_metadata_has_no_secret(self):
        result = OrchestrationResult(results=[_accepted()])
        data = result.as_dict()
        self.assertEqual(data["accepted"], 1)
        self.assertNotIn("secret", str(data).lower())


if __name__ == "__main__":
    unittest.main()
