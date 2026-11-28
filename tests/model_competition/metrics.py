"""Derived throughput metrics for the model-competition harness.

Pure functions only: no network, no Docker, no production imports.

``prefill_tps_observed`` is deliberately named "observed": the TTFT measured by
``full_benchmark.call_stream`` includes gateway, queueing and network time, so
it is a relative comparison figure, not a pure engine prefill measurement.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

Metric = float | int | None


def _token_count(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value < 0:
        return None
    return int(value)


def _milliseconds(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value < 0:
        return None
    return float(value)


def derive_metrics(call: Mapping[str, Any]) -> dict[str, Metric]:
    """Return token counts and throughput derived from one streamed call.

    Missing or malformed ``usage`` data yields ``None`` for every dependent
    metric; it is never estimated into a headline number.
    """
    tokens = call.get("usage") or {}
    if not isinstance(tokens, Mapping):
        tokens = {}

    prompt_tokens = _token_count(tokens.get("prompt_tokens"))
    completion_tokens = _token_count(tokens.get("completion_tokens"))
    ttft_ms = _milliseconds(call.get("ttft_ms"))
    latency_ms = _milliseconds(call.get("latency_ms"))

    decode_tps: Metric = None
    if (
        completion_tokens is not None
        and ttft_ms is not None
        and latency_ms is not None
        and latency_ms > ttft_ms
        and completion_tokens > 0
    ):
        decode_tps = round(completion_tokens / ((latency_ms - ttft_ms) / 1000), 1)

    prefill_tps_observed: Metric = None
    if prompt_tokens is not None and ttft_ms is not None and ttft_ms > 0 and prompt_tokens > 0:
        prefill_tps_observed = round(prompt_tokens / (ttft_ms / 1000), 1)

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "decode_tps": decode_tps,
        "prefill_tps_observed": prefill_tps_observed,
    }
