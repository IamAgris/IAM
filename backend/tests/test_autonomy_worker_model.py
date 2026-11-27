"""OD-39/OD-46: autonomy must not occupy the single local residency slot."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.model_inference import inference_service
from app.workers.autonomy_worker import AutonomyWorker


class AutonomyWorkerModelTests(unittest.IsolatedAsyncioTestCase):
    async def test_reason_uses_explicit_free_hosted_specialist(self):
        response = {
            "choices": [
                {
                    "message": {
                        "content": '{"action":"observe","reasoning":"ok","confidence":0.5}'
                    }
                }
            ],
            "iam_inference": {"model": settings.autonomy_model, "mode": "hosted"},
        }
        status = SimpleNamespace(available=True, mode="hosted", reason="")
        worker = AutonomyWorker()

        with patch.object(
            inference_service, "resolve", new=AsyncMock(return_value=status)
        ), patch.object(
            inference_service, "chat", new=AsyncMock(return_value=response)
        ) as chat:
            decision = await worker._reason({"content": "hi"}, [], object())

        self.assertEqual(chat.await_args.kwargs["model"], settings.autonomy_model)
        self.assertEqual(decision["action"], "observe")
        self.assertTrue(decision["model_used"])
        self.assertEqual(decision["inference_mode"], "hosted")

    async def test_reasoning_engine_forwards_hosted_model(self):
        from app.orchestration.reasoning_engine import ReasoningMode, _call_reasoning_llm

        status = SimpleNamespace(available=True, mode="hosted", reason="")
        response = {
            "choices": [
                {
                    "message": {
                        "content": '{"assumptions":[],"reasoning_steps":[],"conclusion":"ok","confidence":0.5,"identified_gaps":[]}'
                    }
                }
            ]
        }
        with patch.object(
            inference_service, "resolve", new=AsyncMock(return_value=status)
        ), patch.object(
            inference_service, "chat", new=AsyncMock(return_value=response)
        ) as chat:
            parsed = await _call_reasoning_llm(
                object(), ReasoningMode.CAUSAL, "q", [], model=settings.autonomy_model
            )

        self.assertEqual(chat.await_args.kwargs["model"], settings.autonomy_model)
        self.assertEqual(parsed["conclusion"], "ok")

    def test_evaluation_cadence_gate_is_per_node(self):
        from app.orchestration import autonomy_graph as graph

        graph._last_evaluation_at.clear()
        with patch.object(settings, "autonomy_evaluation_interval_s", 300):
            self.assertTrue(graph._evaluation_due("self"))
            self.assertFalse(graph._evaluation_due("self"))
            self.assertTrue(graph._evaluation_due("independent"))


if __name__ == "__main__":
    unittest.main()
