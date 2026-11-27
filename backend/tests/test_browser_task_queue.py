"""Doc 29 WP-04 tests: ARQ browser worker idempotency, deadline and failure."""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.workers import arq_browser_worker as worker


class FakeSessionContext:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *args):
        return None


def patched_worker(terminal_status="queued", expired=False):
    session_cm = MagicMock(return_value=FakeSessionContext())
    evidence = MagicMock()
    evidence.envelope = AsyncMock(return_value={
        "task_id": "task-1", "status": terminal_status, "evidence_refs": [],
    })
    evidence.is_expired = AsyncMock(return_value=expired)
    evidence.set_state = AsyncMock(return_value={"state": "running"})
    evidence.append_audit = AsyncMock(return_value="audit-1")
    evidence.increment_retry = AsyncMock(return_value=1)
    uwaie = MagicMock()
    uwaie.return_value.execute = AsyncMock(return_value={
        "envelope": {"task_id": "task-1", "status": "completed"},
    })
    return (
        patch.object(worker, "AsyncSessionLocal", session_cm),
        patch.object(worker, "BrowserEvidenceService", MagicMock(return_value=evidence)),
        patch.object(worker, "UWAIEService", uwaie),
        evidence,
        uwaie,
    )


PAYLOAD = {
    "task_id": "task-1",
    "steps": [{"action": "navigate", "target": "https://example.com"}],
    "verification": {"expected_text": "Example Domain"},
    "session_token": "session-1",
}


class BrowserWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_terminal_task_is_not_replayed(self):
        patches = patched_worker(terminal_status="completed")
        with patches[0], patches[1], patches[2]:
            result = await worker.run_browser_task({}, **PAYLOAD)
        self.assertEqual(result["status"], "completed")
        patches[4].return_value.execute.assert_not_awaited()

    async def test_expired_task_is_timed_out_without_execution(self):
        patches = patched_worker(expired=True)
        with patches[0], patches[1], patches[2]:
            result = await worker.run_browser_task({}, **PAYLOAD)
        self.assertEqual(result["status"], "queued")  # stored envelope until transition
        patches[3].set_state.assert_awaited_with("task-1", "timed_out")
        patches[4].return_value.execute.assert_not_awaited()

    async def test_failure_records_state_and_bounded_retry(self):
        patches = patched_worker()
        patches[4].return_value.execute = AsyncMock(side_effect=RuntimeError("browser died"))
        with patches[0], patches[1], patches[2]:
            with self.assertRaises(RuntimeError):
                await worker.run_browser_task({}, **PAYLOAD)
        patches[3].set_state.assert_awaited_with("task-1", "failed")
        patches[3].increment_retry.assert_awaited_once_with("task-1")

    async def test_worker_registers_only_browser_task_job(self):
        self.assertEqual(worker.WorkerSettings.functions, [worker.run_browser_task])


if __name__ == "__main__":
    unittest.main()
