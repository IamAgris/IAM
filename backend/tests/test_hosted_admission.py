"""OD-51/OD-39: hosted specialists must not consume a local residency slot."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.services.model_inference import (
    InferenceStatus,
    ProviderCallContext,
    inference_service,
)


def _hosted_route():
    return (
        "nv-nvidia-free",
        "hosted",
        InferenceStatus(True, "hosted", "nv-nvidia-free", [], "ok", "local-qwen-coder-3b"),
    )


class HostedAdmissionTests(unittest.IsolatedAsyncioTestCase):
    async def test_hosted_call_is_admitted_without_irwm_refusal(self):
        context = ProviderCallContext("nvidia", False, None, None)
        with patch.object(inference_service, "_route", new=AsyncMock(return_value=_hosted_route())), \
             patch.object(inference_service, "_prepare_provider_call", new=AsyncMock(return_value=context)), \
             patch.object(inference_service, "_chat_completion", new=AsyncMock(
                 return_value={"choices": [{"message": {"content": "ok"}}]}
             )):
            result = await inference_service.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(result["choices"][0]["message"]["content"], "ok")

    async def test_three_hosted_specialists_run_in_parallel(self):
        context = ProviderCallContext("nvidia", False, None, None)

        async def complete(*args, **kwargs):
            await asyncio.sleep(0.01)
            return {"choices": [{"message": {"content": "ok"}}]}

        with patch.object(inference_service, "_route", new=AsyncMock(return_value=_hosted_route())), \
             patch.object(inference_service, "_prepare_provider_call", new=AsyncMock(return_value=context)), \
             patch.object(inference_service, "_chat_completion", new=AsyncMock(side_effect=complete)):
            results = await asyncio.gather(
                *[inference_service.chat([{"role": "user", "content": "hi"}]) for _ in range(3)]
            )
        self.assertEqual(len(results), 3)
        self.assertTrue(all(r["choices"][0]["message"]["content"] == "ok" for r in results))


if __name__ == "__main__":
    unittest.main()
