"""Provider compatibility subsystem: profiles, translation, parsing, diagnostics."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services.iam_tool_manifest import callable_manifests
from app.services.provider_compat import (
    ToolCallAssembler,
    build_tool_schemas,
    filter_request_parameters,
    forced_tool_choice,
    get_compatibility_profile,
    preserve_reasoning,
    provider_for_model,
    validate_arguments,
)
from app.services.provider_compat.probes import ProbeResult, run_compatibility_probes
from app.services.provider_compat.diagnostics import (
    CompatibilityResult,
    as_dict,
    record_result,
    redact_detail,
)
from app.services.provider_compat.profiles import CompatibilityProfile


class ProviderCompatibilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_profile_source_is_inferred_from_mode(self):
        self.assertEqual(provider_for_model("ollama", "qwen2.5:3b"), "ollama")
        self.assertEqual(
            provider_for_model("hosted", "nvidia-nemotron-3.5-lightning"), "nvidia"
        )
        self.assertEqual(provider_for_model("hosted", "mistralai/x"), "nvidia")

    async def test_live_catalogue_facts_override_defaults(self):
        row = SimpleNamespace(
            tool_calling=True,
            reasoning=False,
            context_length=128000,
            restrictions={"unsupported_parameters": ["prompt_cache_key", "seed"]},
            last_tested=None,
        )

        class FakeResult:
            def scalar_one_or_none(self):
                return row

        class FakeDb:
            async def execute(self, statement):
                return FakeResult()

        profile = await get_compatibility_profile(
            FakeDb(), "hosted", "nvidia-nemotron-3.5-lightning"
        )
        self.assertEqual(profile.unsupported_parameters, ("prompt_cache_key", "seed"))
        self.assertEqual(profile.context_length, 128000)

    async def test_schema_translation_for_hosted_and_local(self):
        hosted = CompatibilityProfile(provider="nvidia", model="x")
        local = CompatibilityProfile(
            provider="ollama", model="x", tool_name_style="dotted"
        )
        hosted_schemas = build_tool_schemas(hosted, callable_manifests())
        local_schemas = build_tool_schemas(local, callable_manifests())
        hosted_names = {s["function"]["name"] for s in hosted_schemas}
        local_names = {s["function"]["name"] for s in local_schemas}
        self.assertIn("tone_analyze", hosted_names)
        self.assertIn("tone.analyze", local_names)
        self.assertTrue(all("." not in n for n in hosted_names))
        tone = next(s for s in hosted_schemas if s["function"]["name"] == "tone_analyze")
        self.assertEqual(tone["function"]["parameters"]["required"], ["text"])

    async def test_request_filtering_removes_only_declared_parameters(self):
        profile = CompatibilityProfile(
            provider="nvidia",
            model="x",
            unsupported_parameters=("prompt_cache_key",),
        )
        filtered, removed = filter_request_parameters(
            profile,
            {
                "model": "x",
                "temperature": 0.4,
                "prompt_cache_key": "secret-ish",
                "max_tokens": 128,
            },
        )
        self.assertEqual(removed, ["prompt_cache_key"])
        self.assertNotIn("prompt_cache_key", filtered)
        self.assertEqual(filtered["temperature"], 0.4)
        self.assertEqual(filtered["max_tokens"], 128)

    async def test_forced_tool_choice_is_profile_gated_and_name_translated(self):
        hosted = CompatibilityProfile(
            provider="nvidia", model="x", supports_forced_tools=True
        )
        local = CompatibilityProfile(
            provider="ollama", model="x", tool_name_style="dotted"
        )
        self.assertIsNone(forced_tool_choice(local, "tone.analyze"))
        self.assertEqual(
            forced_tool_choice(hosted, "tone.analyze"),
            {"type": "function", "function": {"name": "tone_analyze"}},
        )

    async def test_reasoning_field_is_preserved_or_dropped(self):
        keep = CompatibilityProfile(provider="nvidia", model="x", reasoning=True)
        drop = CompatibilityProfile(
            provider="nvidia", model="x", preserve_reasoning=False
        )
        message = {"role": "assistant", "content": "", "reasoning_content": "steps"}
        self.assertEqual(preserve_reasoning(keep, message)["reasoning_content"], "steps")
        self.assertNotIn("reasoning_content", preserve_reasoning(drop, message))

    async def test_streaming_tool_call_assembly(self):
        assembler = ToolCallAssembler()
        assembler.add_delta(0, call_id="call_1")
        assembler.add_delta(0, name="tone_analyze")
        assembler.add_delta(0, arguments='{"text":')
        assembler.add_delta(0, arguments='"hello world"}')
        calls = assembler.calls()
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].complete)
        self.assertEqual(calls[0].id, "call_1")
        self.assertEqual(json.loads(calls[0].arguments), {"text": "hello world"})

    async def test_incomplete_and_duplicate_calls(self):
        incomplete = ToolCallAssembler()
        incomplete.add_delta(0, call_id="c1", name="tone_analyze", arguments='{"text":')
        self.assertEqual(incomplete.incomplete(), [0])

        duplicate = ToolCallAssembler()
        duplicate.add_delta(0, call_id="c1", name="tone_analyze", arguments='{"text":"x"}')
        duplicate.add_delta(1, call_id="c1", name="tone_analyze", arguments='{"text":"x"}')
        self.assertEqual(len(duplicate.executable()), 1)

    async def test_canonical_argument_validation(self):
        self.assertIn("missing:text", validate_arguments("tone_analyze", {}))
        self.assertIn(
            "invalid_type:text", validate_arguments("tone_analyze", {"text": 5})
        )
        self.assertEqual(validate_arguments("tone_analyze", {"text": "ok"}), [])

    async def test_probe_suite_runs_checks_and_persists_result(self):
        row = SimpleNamespace(
            tool_calling=True,
            reasoning=True,
            context_length=128000,
            restrictions={},
            last_tested=None,
            test_result=None,
        )

        class FakeResult:
            def scalar_one_or_none(self):
                return row

        class FakeDb:
            def __init__(self):
                self.commit = AsyncMock()
                self.rollback = AsyncMock()
                self.flush = AsyncMock()
                self.add = lambda event: None

            async def execute(self, statement):
                return FakeResult()

        chat_result = {
            "iam_inference": {
                "tools_offered": True,
                "compatibility": {},
                "tools_executed": [{"name": "tone_analyze", "error": None}],
            }
        }

        async def fake_stream(*args, **kwargs):
            yield {"event": "tool_executed", "data": {"count": 1}}

        db = FakeDb()
        with patch(
            "app.services.provider_compat.probes.inference_service.chat",
            new=AsyncMock(return_value=chat_result),
        ), patch(
            "app.services.provider_compat.probes.inference_service.stream",
            new=fake_stream,
        ):
            results = await run_compatibility_probes(
                db, "nvidia", "nvidia-nemotron-3.5-lightning"
            )

        checks = {item.check for item in results}
        self.assertIn("basic_inference", checks)
        self.assertIn("tool_schema", checks)
        self.assertIn("forced_tool", checks)
        self.assertIn("streaming_tool", checks)
        self.assertIn("parallel_tool_calls", checks)
        self.assertTrue(all(item.status == "accepted" for item in results if item.check != "parallel_tool_calls"))
        db.commit.assert_awaited()
        self.assertIsNotNone(row.test_result)

    async def test_probe_retries_keep_the_best_pass(self):
        from app.services.provider_compat import probes as probe_module

        poor = [ProbeResult("tool_schema", "error", "InferenceUnavailable")]
        good = [ProbeResult("tool_schema", "accepted", "ok")]
        with patch.object(
            probe_module, "_run_probe_once", new=AsyncMock(side_effect=[poor, good])
        ), patch.object(probe_module, "_persist", new=AsyncMock()):
            results = await probe_module.run_compatibility_probes(
                object(), "nvidia", "x", retries=1, retry_delay_seconds=0
            )
        self.assertEqual(results, good)

    async def test_diagnostics_record_only_safe_details(self):
        detail = redact_detail("  Bad 'Bearer abc.def' token  ")
        self.assertIn("Bad", detail)
        self.assertLessEqual(len(detail), 300)
        result = CompatibilityResult(
            provider="nvidia",
            model="x",
            check="tool_schema",
            status="rejected",
            http_status=400,
            detail="error",
        )
        self.assertEqual(as_dict(result)["check"], "tool_schema")
        db = SimpleNamespace(add=lambda event: None, flush=AsyncMock())
        self.assertTrue(await record_result(db, result))
        db.flush.assert_awaited_once()
