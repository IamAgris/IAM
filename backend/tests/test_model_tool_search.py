"""Model-initiated web search is allow-listed, bounded and returns untrusted evidence."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from app.services.model_inference import InferenceService, inference_service


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)[:300]

    def json(self):
        return self._payload


def tool_call_response():
    return FakeResponse(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {
                                    "name": "web_search",
                                    "arguments": json.dumps({"query": "latest news"}),
                                },
                            }
                        ],
                    }
                }
            ]
        }
    )


def final_response(text="Here are the live sources."):
    return FakeResponse(
        {"choices": [{"message": {"role": "assistant", "content": text}}]}
    )


class ModelToolSearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_web_search_is_executed(self):
        service = InferenceService()
        rejected = await service.execute_tool_call({"name": "delete_file", "arguments": "{}"})
        self.assertIn("not permitted", rejected["error"])
        malformed = await service.execute_tool_call(
            {"name": "web_search", "arguments": "not json"}
        )
        self.assertIn("malformed", malformed["error"])

    async def test_web_search_returns_untrusted_evidence(self):
        service = InferenceService()
        evidence = SimpleNamespace(
            provider="duckduckgo-http",
            results=[
                {
                    "title": "Story",
                    "url": "https://example.org/story",
                    "published": "2026-11-27",
                    "claim_label": "single_source",
                }
            ],
            errors=[],
        )
        with patch(
            "app.services.live_information_policy.collect_live_evidence",
            new=AsyncMock(return_value=evidence),
        ) as collect:
            outcome = await service.execute_tool_call(
                {"name": "web_search", "arguments": json.dumps({"query": "latest news"})}
            )
        collect.assert_awaited_once()
        self.assertEqual(outcome["sources"][0]["url"], "https://example.org/story")
        self.assertIn("untrusted", outcome["note"])

    async def test_chat_executes_tool_call_then_answers(self):
        status = SimpleNamespace(primary="local-qwen-3b")
        responses = [tool_call_response(), final_response()]
        outcome = {"query": "latest news", "sources": [], "errors": [], "note": "untrusted"}

        async def fake_execute(call, db=None):
            return outcome

        with patch(
            "app.services.model_inference._post_with_retry",
            new=AsyncMock(side_effect=responses),
        ), patch.object(inference_service, "execute_tool_call", new=AsyncMock(side_effect=fake_execute)):
            result = await inference_service._chat_completion(
                "qwen2.5:3b",
                "ollama",
                status,
                [{"role": "user", "content": "latest news?"}],
                0.7,
                256,
                60.0,
                None,
                allow_tools=True,
            )

        meta = result["iam_inference"]
        self.assertEqual(meta["tool_rounds"], 1)
        self.assertEqual(len(meta["tools_executed"]), 1)
        self.assertTrue(meta["tools_offered"])
        self.assertEqual(result["choices"][0]["message"]["content"], "Here are the live sources.")

    async def test_stream_executes_tool_then_streams_grounded_answer(self):
        tool_json = json.dumps(
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call-1",
                                    "function": {
                                        "name": "web_search",
                                        "arguments": json.dumps({"query": "latest news"}),
                                    },
                                }
                            ]
                        }
                    }
                ]
            }
        )
        lines = [f"data: {tool_json}", "data: [DONE]"]

        class FakeStreamResponse:
            status_code = 200

            async def aiter_lines(self):
                for line in lines:
                    yield line

            async def aiter_text(self):
                yield ""

        class FakeStreamClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            def stream(self, *_args, **_kwargs):
                class Ctx:
                    async def __aenter__(self):
                        return FakeStreamResponse()

                    async def __aexit__(self, *_a):
                        return False

                return Ctx()

        status = SimpleNamespace(primary="local-qwen-3b", available=True, reason="")
        final = final_response("Grounded live answer").json()
        with patch(
            "app.services.model_inference.httpx.AsyncClient",
            side_effect=lambda **_kwargs: FakeStreamClient(),
        ), patch.object(
            inference_service, "_route", new=AsyncMock(return_value=("qwen2.5:3b", "ollama", status))
        ), patch.object(
            inference_service, "_prepare_provider_call",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    provider="ollama", credential=None, decision=None,
                    is_paid=False, key_fingerprint=None,
                )
            ),
        ), patch(
            "app.services.model_inference._admit_inference",
            new=AsyncMock(return_value={"decision": "admit"}),
        ), patch.object(
            inference_service, "execute_tool_call",
            new=AsyncMock(return_value={"query": "latest news", "sources": [], "errors": []}),
        ), patch.object(
            inference_service, "_chat_completion", new=AsyncMock(return_value=final)
        ):
            events = [
                item
                async for item in inference_service.stream(
                    [{"role": "user", "content": "latest news?"}],
                    allow_tools=True,
                )
            ]

        text = "".join(e["data"]["text"] for e in events if e["event"] == "delta")
        self.assertEqual(text.strip(), "Grounded live answer")

    async def test_stream_parses_text_encoded_tool_call(self):
        markup = (
            "<tool_call><function=web_search><parameter=query>"
            "latest news</parameter></function></tool_call>"
        )
        payload = json.dumps({"choices": [{"delta": {"content": markup}}]})
        # Split mid-tag so partial deltas must be buffered before parsing.
        pieces = [markup[:7], markup[7:19], markup[19:]]
        lines = [
            "data: " + json.dumps({"choices": [{"delta": {"content": piece}}]})
            for piece in pieces
        ] + ["data: [DONE]"]

        class FakeStreamResponse:
            status_code = 200

            async def aiter_lines(self):
                for line in lines:
                    yield line

            async def aiter_text(self):
                yield ""

        class FakeStreamClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            def stream(self, *_args, **_kwargs):
                class Ctx:
                    async def __aenter__(self):
                        return FakeStreamResponse()

                    async def __aexit__(self, *_a):
                        return False

                return Ctx()

        status = SimpleNamespace(primary="local-qwen-3b", available=True, reason="")
        final = final_response(
            "<tool_call><function=web_search><parameter=query>x</parameter>"
            "</function></tool_call>"
        ).json()
        with patch(
            "app.services.model_inference.httpx.AsyncClient",
            side_effect=lambda **_kwargs: FakeStreamClient(),
        ), patch.object(
            inference_service, "_route",
            new=AsyncMock(return_value=("qwen2.5:3b", "ollama", status)),
        ), patch.object(
            inference_service, "_prepare_provider_call",
            new=AsyncMock(
                return_value=SimpleNamespace(
                    provider="ollama", credential=None, decision=None,
                    is_paid=False, key_fingerprint=None,
                )
            ),
        ), patch(
            "app.services.model_inference._admit_inference",
            new=AsyncMock(return_value={"decision": "admit"}),
        ), patch.object(
            inference_service, "execute_tool_call",
            new=AsyncMock(
                return_value={
                    "query": "latest news",
                    "sources": [
                        {
                            "title": "Live report",
                            "url": "https://example.org/live",
                            "published": "2026-11-27",
                        }
                    ],
                    "errors": [],
                }
            ),
        ) as execute, patch.object(
            inference_service, "_chat_completion", new=AsyncMock(return_value=final)
        ):
            events = [
                item
                async for item in inference_service.stream(
                    [{"role": "user", "content": "latest news?"}], allow_tools=True
                )
            ]

        execute.assert_awaited_once()
        text = "".join(e["data"]["text"] for e in events if e["event"] == "delta")
        self.assertIn("https://example.org/live", text)
        self.assertIn("2026-11-27", text)
        self.assertNotIn("<tool_call>", text)

    async def test_tools_schema_is_dropped_when_provider_rejects_it(self):
        status = SimpleNamespace(primary="local-qwen-3b")
        responses = [
            FakeResponse({"error": "unsupported"}, status_code=400),
            final_response("plain answer"),
        ]
        with patch(
            "app.services.model_inference._post_with_retry",
            new=AsyncMock(side_effect=responses),
        ):
            result = await inference_service._chat_completion(
                "qwen2.5:3b",
                "ollama",
                status,
                [{"role": "user", "content": "hello"}],
                0.7,
                64,
                60.0,
                None,
                allow_tools=True,
            )
        self.assertFalse(result["iam_inference"]["tools_offered"])
        self.assertEqual(result["choices"][0]["message"]["content"], "plain answer")


if __name__ == "__main__":
    unittest.main()
