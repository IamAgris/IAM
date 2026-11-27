"""Quick feasibility probe at 6 vCPU / 12 GB (one resident model at a time).

Uses the same task/prompt/assertions. Writes to a separate results file so the
main 4 vCPU / 8 GB scorecard is not polluted.

Usage: python tests/model_competition/probe_12gb.py
Requires: docker update --cpus 6 --memory 12g --memory-swap 12g aura-ollama
"""

import json
from pathlib import Path

from full_benchmark import (
    Sampler,
    call_stream,
    cgroup_snapshot,
    restart_ollama,
)
from smoke_coding import extract_code, run_candidate

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "probe_12gb.jsonl"
CASES = [
    ("local-qwen-coder-3b", None),
    ("local-qwen-3b", None),
    ("local-qwen3.5-4b", {"think": False}),
]


def probe(model: str, extra_body, phase: str):
    if phase == "cold":
        restart_ollama()
    cgroup_snapshot()
    sampler = Sampler()
    sampler.start()
    call = call_stream(model, extra_body)
    sampler.stop()
    cg1 = cgroup_snapshot()
    code = extract_code(call["reply"])
    passed, detail = run_candidate(code)
    metrics = sampler.metrics()
    return {
        "model": model,
        "thinking_disabled": bool(extra_body),
        "quota_cores": cg1["quota_cores"],
        "memory_limit_gb": round(cg1["memory_max"] / 2**30, 2),
        "latency_ms": call["latency_ms"],
        "ttft_ms": call["ttft_ms"],
        "peak_mem_mb": metrics.get("peak_mem_mb"),
        "swap_peak_mb": metrics.get("swap_peak_mb"),
        "peak_cpu_cores": metrics.get("peak_cpu_cores"),
        "avg_cpu_cores": metrics.get("avg_cpu_cores"),
        "passed": passed,
        "detail": detail[:200],
        "code_chars": len(code),
    }


def main() -> None:
    limits = cgroup_snapshot()
    print("Limits:", limits["cpu_max"], limits["memory_max"])
    with OUT.open("a", encoding="utf-8") as fh:
        for model, extra in CASES:
            for phase in ("cold", "warm"):
                record = probe(model, extra, phase)
                record["phase"] = phase
                fh.write(json.dumps(record) + "\n")
                fh.flush()
                print(json.dumps(record))
    print(f"\nWrote {OUT.relative_to(HERE.parents[2])}")


if __name__ == "__main__":
    main()
