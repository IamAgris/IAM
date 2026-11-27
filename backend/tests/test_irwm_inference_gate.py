"""OD-39: no chat or stream request may reach a provider before IRWM admission."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.model_inference import (
    InferenceUnavailable,
    _admit_inference,
    _estimate_ram_mb,
    _release_inference,
    inference_service,
)


def routed():
    status = SimpleNamespace(available=True, reason="", primary="local-qwen-coder-3b")
    return "local-qwen-coder-3b", "ollama", status


class IRWMInferenceGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_chat_admits_before_completion_and_always_releases(self):
        admission = {"decision": "admit", "model": "local-qwen-coder-3b"}
        events = []

        async def admit(*args, **kwargs):
            events.append("admit")
            return admission

        async def complete(*args, **kwargs):
            events.append("complete")
            return {"choices": [{"message": {"content": "ok"}}]}

        async def release(*args, **kwargs):
            events.append("release")

        with patch.object(inference_service, "_route", new=AsyncMock(return_value=routed())), \
             patch("app.services.model_inference._admit_inference", new=AsyncMock(side_effect=admit)), \
             patch.object(inference_service, "_chat_completion", new=AsyncMock(side_effect=complete)), \
             patch("app.services.model_inference._release_inference", new=AsyncMock(side_effect=release)):
            result = await inference_service.chat([{"role": "user", "content": "hi"}])

        self.assertEqual(result["choices"][0]["message"]["content"], "ok")
        self.assertEqual(events, ["admit", "complete", "release"])

    async def test_chat_fails_closed_when_admission_is_refused(self):
        completion = AsyncMock()
        with patch.object(inference_service, "_route", new=AsyncMock(return_value=routed())), \
             patch("app.services.model_inference._admit_inference",
                   new=AsyncMock(side_effect=InferenceUnavailable("IRWM admission refused: busy"))), \
             patch.object(inference_service, "_chat_completion", completion):
            with self.assertRaisesRegex(InferenceUnavailable, "IRWM admission refused"):
                await inference_service.chat([{"role": "user", "content": "hi"}])
        completion.assert_not_awaited()

    async def test_stream_emits_resource_refused_without_provider_call(self):
        with patch.object(inference_service, "_route", new=AsyncMock(return_value=routed())), \
             patch("app.services.model_inference._admit_inference",
                   new=AsyncMock(side_effect=InferenceUnavailable("IRWM admission refused: queued"))):
            events = [
                event
                async for event in inference_service.stream([{"role": "user", "content": "hi"}])
            ]
        self.assertEqual(events[0]["event"], "error")
        self.assertEqual(events[0]["data"]["code"], "resource_refused")

    async def test_admission_rejects_queue_and_delegate_decisions(self):
        with patch.object(settings, "irwm_enabled", True), patch(
            "app.services.irwm.irwm.admit",
            new=AsyncMock(return_value={"decision": "queue", "reason": "one resident in flight"}),
        ):
            with self.assertRaisesRegex(InferenceUnavailable, "one resident in flight"):
                await _admit_inference("local-qwen-coder-3b", "ollama")

    async def test_admission_marks_user_chat_as_non_preemptible(self):
        with patch.object(settings, "irwm_enabled", True), patch(
            "app.services.irwm.irwm.admit",
            new=AsyncMock(return_value={"decision": "admit"}),
        ) as admit:
            await _admit_inference("local-qwen-3b", "ollama", purpose="user")
        self.assertEqual(admit.await_args.kwargs["purpose"], "user")
        self.assertFalse(admit.await_args.kwargs["preemptible"])

    async def test_ram_estimate_uses_model_size_and_hosted_mode(self):
        self.assertEqual(_estimate_ram_mb("qwen2.5:3b", "ollama"), 1200)
        self.assertEqual(_estimate_ram_mb("qwen3.5-9b", "hosted"), 256)

    async def test_release_forwards_lease_id_to_irwm(self):
        with patch("app.services.irwm.irwm.release", new=AsyncMock()) as release:
            await _release_inference("local-qwen-3b", "ollama", "lease-1")
        release.assert_awaited_once_with("local-qwen-3b", "lease-1")

    async def test_chat_registers_cancellation_release_for_local_lease(self):
        admission = {"decision": "admit", "lease_id": "lease-2"}
        callbacks = []
        fake_task = SimpleNamespace(add_done_callback=lambda cb: callbacks.append(cb))

        async def complete(*args, **kwargs):
            return {"choices": [{"message": {"content": "ok"}}]}

        with patch.object(inference_service, "_route", new=AsyncMock(return_value=routed())), \
             patch("app.services.model_inference._admit_inference",
                   new=AsyncMock(return_value=admission)), \
             patch.object(inference_service, "_chat_completion", new=AsyncMock(side_effect=complete)), \
             patch("app.services.model_inference._release_inference", new=AsyncMock()), \
             patch("app.services.model_inference.asyncio.current_task",
                   return_value=fake_task):
            await inference_service.chat([{"role": "user", "content": "hi"}])

        self.assertEqual(len(callbacks), 1)


if __name__ == "__main__":
    unittest.main()
