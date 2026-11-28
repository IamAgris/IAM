"""OD-52 Phase F: context fitting, retry, tool-call normalisation and validation."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services.model_inference import (
    InferenceStatus,
    InferenceUnavailable,
    InferenceService,
    _fit_context,
    _normalise_tool_calls,
    _post_with_retry,
)


class FakeResponse:
    def __init__(self, status, data=None):
        self.status_code = status
        self._data = data or {}
        self.text = str(data)[:300]

    def json(self):
        return self._data


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, *args, **kwargs):
        self.calls += 1
        return FakeResponse(*self.responses.pop(0))


class PhaseFTests(unittest.IsolatedAsyncioTestCase):
    def test_context_fit_keeps_system_and_recent_messages(self):
        messages = [
            {"role": "system", "content": "x" * 100},
            {"role": "user", "content": "y" * 100},
            {"role": "user", "content": "newest"},
        ]
        fitted = _fit_context(messages, 40)
        self.assertEqual(fitted[0], messages[0])
        self.assertIn(messages[-1], fitted)
        self.assertLessEqual(sum(len(m["content"]) // 4 for m in fitted), 40)

    def test_tool_calls_normalised(self):
        result = _normalise_tool_calls(
            {"tool_calls": [{"id": "1", "function": {"name": "search", "arguments": "{}"}}]}
        )
        self.assertEqual(result, [{"id": "1", "name": "search", "arguments": "{}"}])

    async def test_rate_limit_is_retried(self):
        client = FakeClient([(429, {"error": "slow"}), (200, {"ok": True})])
        with patch("app.services.model_inference.settings.provider_retry_backoff_seconds", 0):
            response = await _post_with_retry(client, "http://x", {}, {}, 1.0)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.calls, 2)

    async def test_malformed_response_is_rejected(self):
        service = InferenceService()
        status = InferenceStatus(True, "hosted", "nv-free", [], "ok", "primary")
        client = FakeClient([(200, {"choices": []})])
        with patch("app.services.model_inference.httpx.AsyncClient", return_value=client):
            with self.assertRaises(InferenceUnavailable):
                await service._chat_completion(
                    "nv-free", "hosted", status, [{"role": "user", "content": "hi"}],
                    0.5, None, 1.0, None,
                )


if __name__ == "__main__":
    unittest.main()
