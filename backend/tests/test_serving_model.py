"""Shared primary model and the self-improvement -> inference bridge (OD-38/OD-40)."""

import tempfile
import unittest
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services import serving_model
from app.services.model_inference import InferenceService


class ServingModelTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = patch.object(settings, "model_release_artifact_root", self.tmp.name)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    async def test_defaults_to_configured_primary(self):
        active = serving_model.current()
        self.assertEqual(active.model, settings.iam_primary_model)
        self.assertEqual(active.source, "config")

    async def test_promotion_and_rollback_restore_previous_model(self):
        serving_model.activate("local-qwen-3b", version="v2", actor="test")
        serving_model.activate("local-qwen-3b", version="v3", actor="test")
        active = serving_model.current()
        self.assertEqual(active.version, "v3")
        self.assertEqual(active.previous, "local-qwen-3b")

        serving_model.rollback()
        restored = serving_model.current()
        self.assertEqual(restored.model, "local-qwen-3b")
        self.assertEqual(restored.source, "rollback")

    async def test_local_primary_wins_over_configured_hosted_key(self):
        service = InferenceService()
        with (
            patch.object(settings, "ollama_enabled", True),
            patch.object(settings, "nvidia_api_key", "fake-key"),
            patch.object(
                service,
                "_ollama_models",
                new=AsyncMock(return_value=[settings.iam_primary_local_tag]),
            ),
        ):
            status = await service.resolve()
        self.assertTrue(status.available)
        self.assertEqual(status.mode, "ollama")
        self.assertEqual(status.model, settings.iam_primary_local_tag)
        self.assertEqual(status.primary, settings.iam_primary_model)

    async def test_explicit_model_selects_hosted_sub_agent(self):
        service = InferenceService()
        with (
            patch.object(settings, "ollama_enabled", True),
            patch.object(settings, "nvidia_api_key", "fake-key"),
            patch.object(
                service,
                "_ollama_models",
                new=AsyncMock(return_value=[settings.iam_primary_local_tag]),
            ),
        ):
            target, mode, status = await service._route(settings.adaptive_delegate_model)
        self.assertEqual(target, settings.adaptive_delegate_model)
        self.assertEqual(mode, "hosted")
        self.assertEqual(status.primary, settings.iam_primary_model)

    async def test_promoted_alias_is_resolved_for_serving(self):
        serving_model.activate(settings.iam_primary_model, version="v9", actor="test")
        service = InferenceService()
        with (
            patch.object(settings, "ollama_enabled", True),
            patch.object(
                service,
                "_ollama_models",
                new=AsyncMock(return_value=[settings.iam_primary_local_tag]),
            ),
        ):
            target, mode, _ = await service._route(None)
        self.assertEqual(target, settings.iam_primary_local_tag)
        self.assertEqual(mode, "ollama")

    async def test_missing_primary_tag_never_substitutes_another_local_model(self):
        service = InferenceService()
        with (
            patch.object(settings, "ollama_enabled", True),
            patch.object(settings, "nvidia_api_key", "fake-key"),
            patch.object(
                service,
                "_ollama_models",
                new=AsyncMock(return_value=["qwen2.5:3b"]),
            ),
        ):
            status = await service.resolve()
            target, mode, _ = await service._route(None)
        self.assertEqual(status.mode, "hosted")
        self.assertEqual(status.model, settings.iam_sdk_default_model)
        self.assertEqual(mode, "hosted")
        self.assertEqual(target, settings.iam_sdk_default_model)

    async def test_approved_secondary_local_alias_still_resolves(self):
        service = InferenceService()
        with (
            patch.object(settings, "ollama_enabled", True),
            patch.object(
                service,
                "_ollama_models",
                new=AsyncMock(return_value=["qwen2.5:3b"]),
            ),
        ):
            target, mode, _ = await service._route("local-qwen-3b")
        self.assertEqual(target, "qwen2.5:3b")
        self.assertEqual(mode, "ollama")

    async def test_chat_uses_configured_cold_start_timeout(self):
        captured = []

        class FakeResponse:
            status_code = 200
            text = ""

            def json(self):
                return {"choices": [{"message": {"content": "ok"}}]}

        class FakeClient:
            def __init__(self, timeout):
                captured.append(timeout)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def post(self, *_args, **_kwargs):
                return FakeResponse()

        service = InferenceService()
        with (
            patch.object(settings, "ollama_enabled", True),
            patch.object(
                service,
                "_ollama_models",
                new=AsyncMock(return_value=[settings.iam_primary_local_tag]),
            ),
            patch("app.services.model_inference.httpx.AsyncClient", FakeClient),
        ):
            result = await service.chat([{"role": "user", "content": "hi"}])
        self.assertEqual(result["iam_inference"]["model"], settings.iam_primary_local_tag)
        self.assertEqual(captured[-1], settings.inference_chat_timeout_seconds)
        self.assertGreaterEqual(settings.inference_chat_timeout_seconds, 300)

    async def test_stream_uses_configured_cold_start_timeout(self):
        captured = []

        class FakeStreamResponse:
            status_code = 200

            async def aiter_lines(self):
                yield 'data: {"choices":[{"delta":{"content":"ok"}}]}'
                yield "data: [DONE]"

        class FakeClient:
            def __init__(self, timeout):
                captured.append(timeout)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            @asynccontextmanager
            async def stream(self, *_args, **_kwargs):
                yield FakeStreamResponse()

        service = InferenceService()
        with (
            patch.object(settings, "ollama_enabled", True),
            patch.object(
                service,
                "_ollama_models",
                new=AsyncMock(return_value=[settings.iam_primary_local_tag]),
            ),
            patch("app.services.model_inference.httpx.AsyncClient", FakeClient),
        ):
            events = [item async for item in service.stream([{"role": "user", "content": "hi"}])]
        self.assertEqual(events[0]["event"], "start")
        self.assertEqual(captured[-1], settings.inference_stream_timeout_seconds)
        self.assertGreaterEqual(settings.inference_stream_timeout_seconds, 300)


if __name__ == "__main__":
    unittest.main()
