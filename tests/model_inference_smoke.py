"""Unit smoke tests for real-inference resolution (no live provider needed).

Run: python tests/model_inference_smoke.py
"""

import asyncio
import json
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import settings
from app.services.model_inference import InferenceService, InferenceUnavailable
import app.services.model_inference as inference_module

ORIGINAL_ASYNC_CLIENT = httpx.AsyncClient


def mock_client_factory(handler):
    def factory(*args, **kwargs):
        kwargs.pop("transport", None)
        return ORIGINAL_ASYNC_CLIENT(
            transport=httpx.MockTransport(handler), *args, **kwargs
        )
    return factory


def serving(model: str):
    return patch.object(
        inference_module.serving_model,
        "current",
        return_value=SimpleNamespace(model=model),
    )


class InferenceResolutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_offline_reports_unavailable_and_never_fabricates(self):
        service = InferenceService()
        with serving("local-qwen-3b"), patch.object(
            settings, "nvidia_api_key", None
        ), patch.object(settings, "dashscope_api_key", None), patch.object(
            settings, "openai_api_key", None
        ), patch.object(settings, "anthropic_api_key", None), patch.object(
            settings, "ollama_enabled", False
        ):
            status = await service.resolve()
            self.assertFalse(status.available)
            self.assertEqual(status.mode, "offline")
            with self.assertRaises(InferenceUnavailable):
                await service.chat([{"role": "user", "content": "hello"}])

    async def test_hosted_key_uses_litellm_without_exposing_key(self):
        captured = {}

        def handler(request):
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("authorization")
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "real hosted reply"}}]},
            )

        service = InferenceService()
        with serving("nvidia-test-model"), patch.object(
            settings, "nvidia_api_key", "test-key"
        ), patch.object(
            inference_module.httpx, "AsyncClient", mock_client_factory(handler)
        ):
            status = await service.resolve()
            self.assertTrue(status.available)
            self.assertEqual(status.mode, "hosted")
            self.assertEqual(status.model, "nvidia-test-model")
            result = await service.chat([{"role": "user", "content": "hello"}])
            self.assertEqual(
                result["choices"][0]["message"]["content"], "real hosted reply"
            )
            self.assertEqual(result["iam_inference"]["mode"], "hosted")
            self.assertIn("/chat/completions", captured["url"])
            self.assertNotIn("test-key", json.dumps(status.as_dict()))

    async def test_opt_in_ollama_discovers_local_model(self):
        def handler(request):
            if request.url.path.endswith("/api/tags"):
                return httpx.Response(200, json={"models": [{"name": "qwen2.5:3b"}]})
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "real local reply"}}]},
            )

        service = InferenceService()
        with serving("local-qwen-3b"), patch.object(
            settings, "nvidia_api_key", None
        ), patch.object(settings, "dashscope_api_key", None), patch.object(
            settings, "openai_api_key", None
        ), patch.object(settings, "anthropic_api_key", None), patch.object(
            settings, "ollama_enabled", True
        ), patch.object(
            settings, "ollama_base_url", "http://ollama-test:11434"
        ), patch.object(
            inference_module.httpx, "AsyncClient", mock_client_factory(handler)
        ):
            status = await service.resolve()
            self.assertEqual(status.mode, "ollama")
            self.assertEqual(status.model, "qwen2.5:3b")
            result = await service.chat([{"role": "user", "content": "hello"}])
            self.assertEqual(
                result["choices"][0]["message"]["content"], "real local reply"
            )
            self.assertEqual(result["iam_inference"]["mode"], "ollama")


if __name__ == "__main__":
    unittest.main(verbosity=2)
