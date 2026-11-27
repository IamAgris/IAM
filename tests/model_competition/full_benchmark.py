"""Full OD-38 local-model benchmark under the emulated Contabo profile.

Conditions (owner instruction):
  - identical task, prompt, models, quantisation and assertions as smoke_coding.py
  - separate cold (Ollama restart) and warm trials, order alternated
  - at least five warm trials per model
  - cgroup-derived CPU/RAM/swap/throttling/OOM, plus TTFT for load overhead
  - median / min / max / variability, never a single-run verdict

Usage: python tests/model_competition/full_benchmark.py
Requires aura-ollama constrained to 4 vCPU / 8 GB (see docker-compose.benchmark.yml).
"""

import json
import statistics
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from smoke_coding import TASK, extract_code, master_key, run_candidate

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "constrained_results.jsonl"
SUMMARY = HERE / "results" / "benchmark_summary.json"
CONTAINER = "aura-ollama"
MODELS = ["local-qwen-coder-3b", "local-qwen-3b", "local-qwen3.5-4b"]
TAGS = {
    "local-qwen-coder-3b": "qwen2.5-coder:3b",
    "local-qwen-3b": "qwen2.5:3b",
    "local-qwen3.5-4b": "qwen3.5:4b",
}

CGROUP_CMD = (
    "cat /sys/fs/cgroup/cpu.max; echo ---; "
    "cat /sys/fs/cgroup/memory.max; echo ---; "
    "cat /sys/fs/cgroup/memory.current; echo ---; "
    "cat /sys/fs/cgroup/memory.swap.current; echo ---; "
    "cat /sys/fs/cgroup/memory.events; echo ---; "
    "cat /sys/fs/cgroup/cpu.stat"
)


def docker(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=timeout
    )


def cgroup_snapshot() -> dict:
    proc = docker("exec", CONTAINER, "sh", "-c", CGROUP_CMD)
    if proc.returncode != 0:
        raise RuntimeError(f"cgroup read failed: {proc.stderr.strip()[:300]}")
    parts = [p.strip() for p in proc.stdout.split("---")]
    cpu_max = parts[0]
    quota, period = (int(x) for x in cpu_max.split())
    events = dict(line.split() for line in parts[4].splitlines() if len(line.split()) == 2)
    stats = dict(line.split() for line in parts[5].splitlines() if len(line.split()) == 2)
    return {
        "cpu_max": cpu_max,
        "quota_cores": quota / period,
        "memory_max": int(parts[1]),
        "memory_current": int(parts[2]),
        "swap_current": int(parts[3]),
        "events": events,
        "usage_usec": int(stats.get("usage_usec", 0)),
        "throttled": int(stats.get("nr_throttled", 0)),
        "throttled_usec": int(stats.get("throttled_usec", 0)),
    }


def ollama_ps() -> str:
    return docker("exec", CONTAINER, "ollama", "ps").stdout


def wait_healthy(timeout: int = 180) -> None:
    deadline = time.time() + timeout
    health = "unknown"
    while time.time() < deadline:
        proc = docker(
            "inspect",
            CONTAINER,
            "--format",
            "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
        )
        health = proc.stdout.strip()
        if health in ("healthy", "none"):
            return
        time.sleep(2)
    raise RuntimeError(f"Ollama did not become healthy (last={health})")


def restart_ollama() -> None:
    docker("restart", CONTAINER, timeout=120)
    wait_healthy()


class Sampler:
    def __init__(self):
        self.samples = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        while not self._stop.is_set():
            try:
                cg = cgroup_snapshot()
                self.samples.append(
                    {
                        "t": time.perf_counter(),
                        "mem": cg["memory_current"],
                        "swap": cg["swap_current"],
                        "usage": cg["usage_usec"],
                        "throttled": cg["throttled"],
                        "events": cg["events"],
                    }
                )
            except Exception:
                pass
            self._stop.wait(0.2)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=10)

    def metrics(self):
        if len(self.samples) < 2:
            return {}
        cores = []
        for a, b in zip(self.samples, self.samples[1:]):
            dt_us = (b["t"] - a["t"]) * 1e6
            du = b["usage"] - a["usage"]
            if dt_us > 0 and du >= 0:
                cores.append(du / dt_us)
        first, last = self.samples[0], self.samples[-1]
        return {
            "idle_mem_mb": round(first["mem"] / 2**20, 1),
            "peak_mem_mb": round(max(s["mem"] for s in self.samples) / 2**20, 1),
            "post_mem_mb": round(last["mem"] / 2**20, 1),
            "swap_peak_mb": round(max(s["swap"] for s in self.samples) / 2**20, 1),
            "avg_cpu_cores": round(statistics.mean(cores), 2) if cores else None,
            "peak_cpu_cores": round(max(cores), 2) if cores else None,
            "throttled_delta": last["throttled"] - first["throttled"],
            "oom_kill_delta": int(last["events"].get("oom_kill", 0))
            - int(first["events"].get("oom_kill", 0)),
            "samples": len(self.samples),
        }


def call_stream(model: str, extra_body: dict | None = None) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": TASK}],
        "temperature": 0,
        "max_tokens": 512,
        "stream": True,
    }
    if extra_body:
        body["extra_body"] = extra_body
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        "http://localhost:4000/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {master_key()}",
        },
    )
    started = time.perf_counter()
    ttft = None
    chunks = []
    usage = {}
    with urllib.request.urlopen(req, timeout=900) as resp:
        for raw in resp:
            line = raw.decode("utf-8", "ignore").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = obj.get("choices") or []
            if choices:
                content = (choices[0].get("delta") or {}).get("content") or ""
                if content:
                    if ttft is None:
                        ttft = (time.perf_counter() - started) * 1000
                    chunks.append(content)
            if obj.get("usage"):
                usage = obj["usage"]
    return {
        "reply": "".join(chunks),
        "ttft_ms": round(ttft, 1) if ttft is not None else None,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "usage": usage,
    }


def run_trial(model: str, phase: str, order: int, extra_body: dict | None = None) -> dict:
    if phase == "cold":
        restart_ollama()
    cg0 = cgroup_snapshot()
    loaded_before = TAGS[model] in ollama_ps()
    sampler = Sampler()
    sampler.start()
    call = call_stream(model, extra_body)
    sampler.stop()
    loaded_after = TAGS[model] in ollama_ps()
    code = extract_code(call["reply"])
    passed, detail = run_candidate(code)
    record = {
        "phase": phase,
        "order": order,
        "model": model,
        "passed": passed,
        "detail": detail[:300],
        "ttft_ms": call["ttft_ms"],
        "latency_ms": call["latency_ms"],
        "usage": call["usage"],
        "quota_cores": cg0["quota_cores"],
        "memory_max_bytes": cg0["memory_max"],
        "loaded_before": loaded_before,
        "loaded_after": loaded_after,
        "thinking_disabled": bool(extra_body and extra_body.get("think") is False),
        "code": code[:600],
        **sampler.metrics(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    print(
        f"[{order:02d}] {phase:4} {model:22} "
        f"ttft={record['ttft_ms']}ms total={record['latency_ms']}ms "
        f"peak={record.get('peak_cpu_cores')}cores/{record.get('peak_mem_mb')}MB "
        f"pass={passed}"
    )
    return record


def summarise(records: list):
    summary = {}
    for model in MODELS:
        cold = [r for r in records if r["model"] == model and r["phase"] == "cold"]
        warm = [r for r in records if r["model"] == model and r["phase"] == "warm"]
        lat = [r["latency_ms"] for r in warm]
        ttft = [r["ttft_ms"] for r in warm if r["ttft_ms"] is not None]
        cold_ttft = [r["ttft_ms"] for r in cold if r["ttft_ms"] is not None]

        def stats(values):
            if not values:
                return {}
            return {
                "n": len(values),
                "min": round(min(values), 1),
                "median": round(statistics.median(values), 1),
                "max": round(max(values), 1),
                "stdev": round(statistics.stdev(values), 1) if len(values) > 1 else 0,
            }

        summary[model] = {
            "cold": {
                "latency_ms": stats([r["latency_ms"] for r in cold]),
                "ttft_ms": stats(cold_ttft),
                "peak_mem_mb": stats([r["peak_mem_mb"] for r in cold]),
                "correct": sum(r["passed"] for r in cold),
            },
            "warm": {
                "latency_ms": stats(lat),
                "ttft_ms": stats(ttft),
                "peak_mem_mb": stats([r["peak_mem_mb"] for r in warm]),
                "avg_cpu_cores": stats(
                    [r["avg_cpu_cores"] for r in warm if r["avg_cpu_cores"] is not None]
                ),
                "peak_cpu_cores": stats(
                    [r["peak_cpu_cores"] for r in warm if r["peak_cpu_cores"] is not None]
                ),
                "correct": sum(r["passed"] for r in warm),
            },
            "load_overhead_ms_estimate": (
                round(statistics.median(cold_ttft) - statistics.median(ttft), 1)
                if cold_ttft and ttft
                else None
            ),
            "oom_kills": sum(r.get("oom_kill_delta", 0) for r in cold + warm),
            "throttled_periods": sum(r.get("throttled_delta", 0) for r in cold + warm),
        }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("\n" + json.dumps(summary, indent=2))
    print(f"\nWrote {SUMMARY.relative_to(HERE.parents[2])}")


def main() -> int:
    cg0 = cgroup_snapshot()
    print(f"Effective quota: {cg0['cpu_max']} -> {cg0['quota_cores']} cores; "
          f"memory.max={cg0['memory_max'] / 2**30:.1f} GiB")

    plan = []
    order = 0
    # Cold rounds: alternate which model runs first.
    for seq in (MODELS, MODELS[::-1]):
        for model in seq:
            order += 1
            plan.append(("cold", model, order))
    # Five warm rounds, alternating order each round.
    for round_no in range(5):
        seq = MODELS if round_no % 2 == 0 else MODELS[::-1]
        for model in seq:
            order += 1
            plan.append(("warm", model, order))

    records = []
    for phase, model, idx in plan:
        records.append(run_trial(model, phase, idx))
    summarise(records)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
