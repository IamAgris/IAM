"""Stability check: concurrent identical requests through LiteLLM.

Uses the same TASK, prompt and assertions as the rest of the comparison.
Three requests are released together per model; records per-request latency,
correctness and container resource peaks.

Usage: python tests/model_competition/concurrent_check.py
"""

import json
import statistics
import threading
import time
from pathlib import Path

from full_benchmark import MODELS, Sampler, call_stream, cgroup_snapshot
from metrics import derive_metrics
from smoke_coding import extract_code, run_candidate

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "concurrent_results.jsonl"
N = 3


def median_or_none(values: list) -> float | None:
    present = [v for v in values if v is not None]
    return round(statistics.median(present), 1) if present else None


def check_model(model: str) -> dict:
    barrier = threading.Barrier(N)
    results = [None] * N

    def worker(idx: int):
        barrier.wait()
        call = call_stream(model)
        code = extract_code(call["reply"])
        passed, detail = run_candidate(code)
        results[idx] = {
            "ttft_ms": call["ttft_ms"],
            "latency_ms": call["latency_ms"],
            **derive_metrics(call),
            "passed": passed,
            "detail": detail[:200],
        }

    cg0 = cgroup_snapshot()
    sampler = Sampler()
    sampler.start()
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=300)
    sampler.stop()
    cg1 = cgroup_snapshot()

    latencies = [r["latency_ms"] for r in results if r]
    record = {
        "model": model,
        "concurrent_requests": N,
        "passed": sum(r["passed"] for r in results if r),
        "latencies_ms": latencies,
        "median_latency_ms": round(statistics.median(latencies), 1) if latencies else None,
        "max_latency_ms": round(max(latencies), 1) if latencies else None,
        "ttft_ms": [r["ttft_ms"] for r in results if r],
        "prompt_tokens": [r["prompt_tokens"] for r in results if r],
        "completion_tokens": [r["completion_tokens"] for r in results if r],
        "decode_tps": [r["decode_tps"] for r in results if r],
        "prefill_tps_observed": [r["prefill_tps_observed"] for r in results if r],
        "median_decode_tps": median_or_none([r["decode_tps"] for r in results if r]),
        "median_prefill_tps_observed": median_or_none(
            [r["prefill_tps_observed"] for r in results if r]
        ),
        "peak_mem_mb": round(cg1["memory_current"] / 2**20, 1),
        "peak_swap_mb": round(cg1["swap_current"] / 2**20, 1),
        "throttled_delta": cg1["throttled"] - cg0["throttled"],
        "oom_kills": int(cg1["events"].get("oom_kill", 0))
        - int(cg0["events"].get("oom_kill", 0)),
        "details": [r["detail"] for r in results if r],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    print(json.dumps({k: v for k, v in record.items() if k != "details"}, indent=2))
    return record


def main() -> None:
    for i, model in enumerate(MODELS):
        if i:
            time.sleep(5)
        check_model(model)


if __name__ == "__main__":
    main()
