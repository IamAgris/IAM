"""Integration tests for the durable cognitive lifecycle.

Each test exercises a real graph node with its downstream IAM service replaced
by a deterministic fake, proving that the node performs the integration rather
than returning a hard-coded status. No test weakens an authority gate.
"""

import json
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.orchestration import autonomy_graph, dispatch


class FakeResult:
    def __init__(self, value=None, values=None):
        self.value = value
        self.values = values or []

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


class FakeSession:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.added = []
        self.commits = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def execute(self, statement):
        if self.results:
            return self.results.pop(0)
        return FakeResult()

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


def patch_db(session):
    return patch("app.core.database.get_session_factory", return_value=lambda: session)


def base_state(**overrides):
    state = {
        "session_id": "test",
        "trigger": "unit",
        "observations": [],
        "memories": [],
        "steps": [],
        "retry_count": 0,
        "decision": None,
        "authority_check": {"permitted": True},
    }
    state.update(overrides)
    return state


class CognitiveLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_observe_reads_real_goals_and_tasks(self):
        goal = SimpleNamespace(id=uuid.uuid4(), title="Independent infrastructure")
        task = SimpleNamespace(id=uuid.uuid4(), title="Research providers", tool_used=None)
        session = FakeSession([FakeResult(values=[goal]), FakeResult(values=[task])])
        with patch_db(session):
            result = await autonomy_graph.observe(base_state())
        self.assertEqual(
            [item["type"] for item in result["observations"]], ["goal", "task"]
        )
        self.assertEqual(result["observations"][1]["title"], "Research providers")

    async def test_retrieve_memory_uses_memory_service(self):
        found = [{"id": "mem-1", "content": "prior research", "topic": "research", "similarity": 0.8}]
        session = FakeSession()
        with patch_db(session), patch(
            "app.services.memory_service.MemoryService.search_memory",
            new_callable=AsyncMock,
            return_value=found,
        ) as recall:
            result = await autonomy_graph.retrieve_memory(
                base_state(observations=[{"type": "task", "title": "research providers"}])
            )
        recall.assert_awaited_once()
        self.assertEqual(result["memories"][0]["id"], "mem-1")
        self.assertIsNone(result["memory_error"])

    async def test_retrieve_memory_reports_failure_without_fabricating(self):
        session = FakeSession()
        with patch_db(session), patch(
            "app.services.memory_service.MemoryService.search_memory",
            new_callable=AsyncMock,
            side_effect=RuntimeError("database down"),
        ):
            result = await autonomy_graph.retrieve_memory(
                base_state(observations=[{"type": "task", "title": "research"}])
            )
        self.assertEqual(result["memories"], [])
        self.assertIn("database down", result["memory_error"])

    async def test_reason_uses_model_and_records_provenance(self):
        inference = SimpleNamespace(
            resolve=AsyncMock(
                return_value=SimpleNamespace(
                    available=True, mode="hosted", model="qwen", reason=""
                )
            ),
            chat=AsyncMock(
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": '{"action": "research", "reasoning": "gap found", "confidence": 0.8}'
                            }
                        }
                    ]
                }
            ),
        )
        with patch("app.services.model_inference.inference_service", inference):
            result = await autonomy_graph.reason(
                base_state(observations=[{"type": "task", "title": "research"}])
            )
        self.assertTrue(result["model_used"])
        self.assertEqual(result["inference_mode"], "hosted")
        self.assertEqual(result["decision"]["action"], "research")

    async def test_reason_offline_fallback_takes_no_autonomous_action(self):
        inference = SimpleNamespace(
            resolve=AsyncMock(side_effect=RuntimeError("no provider"))
        )
        with patch("app.services.model_inference.inference_service", inference):
            result = await autonomy_graph.reason(
                base_state(observations=[{"type": "task", "title": "research"}])
            )
        self.assertFalse(result["model_used"])
        self.assertEqual(result["decision"]["action"], "observe")
        self.assertEqual(result["decision"]["confidence"], 0.0)

    async def test_plan_selects_allowlisted_service_action(self):
        result = await autonomy_graph.plan(
            base_state(
                objectives=[{"type": "task", "id": "t-1", "title": "anything"}],
                decision={"action": "memory_recall", "confidence": 0.7},
            )
        )
        self.assertEqual(result["plan"]["action"], "memory_recall")
        self.assertIn("dispatch:memory_recall", result["plan"]["steps"])

    async def test_execute_dispatches_and_persists_execution_evidence(self):
        task_id = uuid.uuid4()
        task = SimpleNamespace(status="pending", tool_used=None, completed_at=None)
        session = FakeSession([FakeResult(value=task)])
        outcome = {
            "status": "success",
            "service": "MemoryService",
            "evidence": {"count": 2},
        }
        with patch_db(session), patch(
            "app.orchestration.dispatch.dispatch",
            new_callable=AsyncMock,
            return_value=outcome,
        ) as dispatched:
            result = await autonomy_graph.execute(
                base_state(
                    plan={
                        "objective": {"type": "task", "id": str(task_id), "title": "recall"},
                        "action": "memory_recall",
                    },
                    decision={"confidence": 0.7},
                )
            )
        dispatched.assert_awaited_once()
        self.assertEqual(result["action_result"]["status"], "advanced")
        self.assertEqual(task.status, "completed")
        self.assertTrue(any(type(obj).__name__ == "TaskExecution" for obj in session.added))
        self.assertTrue(session.commits >= 2)

    async def test_verify_requires_persisted_evidence(self):
        unverified = await autonomy_graph.verify(
            base_state(action_result={"status": "advanced"})
        )
        self.assertEqual(unverified["verification"], "unverified")

        row = SimpleNamespace(
            outcome=json.dumps({"status": "success", "evidence": {"count": 2}})
        )
        session = FakeSession([FakeResult(value=row)])
        with patch_db(session):
            verified = await autonomy_graph.verify(
                base_state(
                    decision_id=str(uuid.uuid4()),
                    action_result={"status": "advanced", "service": "MemoryService"},
                )
            )
        self.assertEqual(verified["verification"], "verified_by_execution_evidence")
        self.assertEqual(verified["verification_evidence"]["evidence"]["count"], 2)

    async def test_update_memory_only_consolidates_verified_outcomes(self):
        store = AsyncMock(return_value={"id": "mem-9"})
        state = base_state(
            verification="verified_by_execution_evidence",
            reasoning="research completed",
            dispatch_service="ResearchService",
            decision={"confidence": 0.8},
        )
        session = FakeSession()
        with patch_db(session), patch(
            "app.services.memory_service.MemoryService.store_memory", store
        ):
            stored = await autonomy_graph.update_memory(state)
            self.assertEqual(stored["memory_id"], "mem-9")
            skipped = await autonomy_graph.update_memory(base_state(verification="unverified"))
        self.assertEqual(store.await_count, 1)
        self.assertIn("update_memory:skip_unverified", skipped["steps"])

    async def test_failed_execution_selects_bounded_recovery(self):
        self.assertEqual(
            autonomy_graph._after_execute(
                base_state(action_result={"status": "failed"}, retry_count=0)
            ),
            "recover",
        )
        self.assertEqual(
            autonomy_graph._after_execute(
                base_state(action_result={"status": "advanced"}, retry_count=0)
            ),
            "verify",
        )
        self.assertEqual(
            autonomy_graph._after_execute(
                base_state(action_result={"status": "failed"}, retry_count=1)
            ),
            "verify",
        )


class DispatchContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_unknown_action_fails_closed(self):
        result = await dispatch.dispatch(FakeSession(), "delete_everything", {})
        self.assertEqual(result["status"], "failure")
        self.assertEqual(result["error"], "unknown_action")

    async def test_memory_recall_calls_real_service(self):
        with patch(
            "app.services.memory_service.MemoryService.search_memory",
            new_callable=AsyncMock,
            return_value=[{"id": "m1"}],
        ):
            result = await dispatch.dispatch(
                FakeSession(), "memory_recall", {"query": "IAM", "limit": 2}
            )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["service"], "MemoryService")
        self.assertEqual(result["evidence"]["count"], 1)

    async def test_dispatch_failure_does_not_become_success(self):
        with patch(
            "app.services.capability_service.CapabilityService.list_capabilities",
            new_callable=AsyncMock,
            side_effect=RuntimeError("unavailable"),
        ):
            result = await dispatch.dispatch(FakeSession(), "capability_inspect", {})
        self.assertEqual(result["status"], "failure")
        self.assertNotIn("evidence", result)


    async def test_authority_check_uses_selected_action(self):
        governance = SimpleNamespace(
            get_authority_boundaries=AsyncMock(return_value=[]),
            check_authority=AsyncMock(return_value={"permitted": True}),
        )
        with (
            patch_db(FakeSession()),
            patch(
                "app.services.governance_service.GovernanceService",
                return_value=governance,
            ),
        ):
            result = await autonomy_graph.check_authority(
                base_state(plan={"action": "research"})
            )
        self.assertEqual(result["authority_check"]["action"], "research")
        self.assertTrue(result["authority_check"]["permitted"])

    async def test_protected_action_requires_signed_authorization(self):
        with (
            patch_db(FakeSession()),
            patch(
                "app.services.creatorapproval_service.CreatorApprovalService.check_authorization",
                new_callable=AsyncMock,
                return_value={"authorized": False},
            ),
        ):
            result = await autonomy_graph.execute(
                base_state(
                    plan={"objective": {"title": "x"}, "action": "model_release"}
                )
            )
        self.assertEqual(result["action_result"]["status"], "blocked")
        self.assertEqual(
            result["action_result"]["code"], "protected_core_authorization_required"
        )

    async def test_execute_refuses_when_authority_was_not_granted(self):
        with patch(
            "app.orchestration.dispatch.dispatch", new_callable=AsyncMock
        ) as dispatched:
            result = await autonomy_graph.execute(
                base_state(
                    plan={"objective": {"title": "x"}, "action": "research"},
                    authority_check={"permitted": False},
                )
            )
        self.assertEqual(result["action_result"]["status"], "blocked")
        dispatched.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
