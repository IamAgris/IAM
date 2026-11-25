"""Run a coding smoke test while sampling Ollama's container resource usage.

Meant for the emulated target profile: `docker update --cpus 4 --memory 8g aura-ollama`
(Contabo VPS 4 = 4 vCPU / 8 GB RAM). Samples CPU% and memory from `docker stats`
while smoke_coding.py runs, and appends a constrained result record.

Usage: python tests/model_competition/run_constrained.py <model_alias>
"""

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "constrained_results.jsonl"
CONTAINER = "aura-ollama"


def parse_mem(value: str) -> float:
    """Convert a docker-stats memory string to MB."""
    part = value.strip().split()[0]
    units = {"B": 1 / 2**20, "KiB": 1 / 2**10, "MiB": 1, "GiB": 2**10, "TiB": 2**20}
    for unit in sorted(units, key=len, reverse=True):
        if part.endswith(unit):
            return float(part[: -len(unit)]) * units[unit]
    try:
        return float(part) / 2**20
    except ValueError:
        return 0.0


def sampler(stop: threading.Event, samples: list) -> None:
    while not stop.is_set():
        try:
            proc = subprocess.run(
                [
                    "docker",
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{.CPUPerc}}|{{.MemUsage}}",
                    CONTAINER,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if proc.returncode == 0 and "|" in proc.stdout:
                cpu, mem = proc.stdout.strip().split("|", 1)
                samples.append(
                    {
                        "cpu_pct": float(cpu.strip().rstrip("%") or 0),
                        "mem_mb": round(parse_mem(mem), 1),
                    }
                )
        except Exception:
            pass
        stop.wait(0.5)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_constrained.py <model_alias>", file=sys.stderr)
        return 64
    model = sys.argv[1]

    samples: list = []
    stop = threading.Event()
    thread = threading.Thread(target=sampler, args=(stop, samples), daemon=True)
    thread.start()

    started = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, str(HERE / "smoke_coding.py"), model],
        capture_output=True,
        text=True,
        timeout=900,
    )
    wall_ms = (time.perf_counter() - started) * 1000
    stop.set()
    thread.join(timeout=5)

    try:
        result = json.loads(proc.stdout[proc.stdout.index("{") :])
    except Exception:
        result = {"passed": False, "error": (proc.stderr or proc.stdout)[:500]}

    cpus = [s["cpu_pct"] for s in samples]
    mems = [s["mem_mb"] for s in samples]
    record = {
        "model": model,
        "profile": "4 vCPU / 8 GB (docker update on aura-ollama)",
        "passed": result.get("passed"),
        "detail": result.get("detail", "")[:300],
        "latency_ms": result.get("latency_ms"),
        "wall_ms": round(wall_ms, 1),
        "tokens": result.get("usage", {}).get("total_tokens"),
        "peak_cpu_pct": max(cpus) if cpus else None,
        "avg_cpu_pct": round(sum(cpus) / len(cpus), 1) if cpus else None,
        "peak_mem_mb": max(mems) if mems else None,
        "samples": len(samples),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
    print(json.dumps(record, indent=2))
    return 0 if record["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
