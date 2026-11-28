"""Capture Phase 1 hardware/compatibility evidence for the OD-38 competition.

Run this ON THE TARGET MACHINE (the Contabo VPS 4) for final evidence:
    python tests/model_competition/hardware_evidence.py --target
Without --target the record is labelled DEV (not representative).

Collects host RAM/CPU/disk, container limits, effective cgroup quota, swap and
OOM counters, other containers' memory use, and Ollama model residency.
Writes JSON to tests/model_competition/results/hardware_<host>.json.
"""

import argparse
import json
import platform
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RESULTS = Path(__file__).resolve().parent / "results"


def run(cmd: list, timeout: int = 30):
    try:
        return subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return subprocess.CompletedProcess(cmd, 1, "", str(exc))


def host_memory() -> dict:
    if platform.system() == "Windows":
        ps = (
            "$o = Get-CimInstance Win32_OperatingSystem; "
            "'{0}|{1}' -f $o.TotalVisibleMemorySize, $o.FreePhysicalMemory"
        )
        proc = run(["powershell", "-NoProfile", "-Command", ps])
        if proc.returncode == 0 and "|" in proc.stdout:
            total_kb, free_kb = proc.stdout.strip().split("|")
            return {
                "total_gb": round(int(total_kb) / 2**20, 2),
                "available_gb": round(int(free_kb) / 2**20, 2),
                "source": "Win32_OperatingSystem",
            }
    try:
        info = Path("/proc/meminfo").read_text(encoding="utf-8")
        values = {
            line.split(":")[0]: int(line.split()[1])
            for line in info.splitlines()
            if ":" in line and line.split()[1].isdigit()
        }
        return {
            "total_gb": round(values.get("MemTotal", 0) / 2**20, 2),
            "available_gb": round(values.get("MemAvailable", 0) / 2**20, 2),
            "source": "/proc/meminfo",
        }
    except (OSError, ValueError) as exc:
        return {"error": str(exc)}


def compose_limits() -> dict:
    proc = run(
        ["docker", "compose", "config", "--format", "json"], timeout=60
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()[:300]}
    cfg = json.loads(proc.stdout)
    ollama = cfg.get("services", {}).get("ollama", {})
    deploy = ollama.get("deploy", {}).get("resources", {})
    return {
        "base_compose": deploy.get("limits"),
        "base_reservations": deploy.get("reservations"),
    }


def container_limits(name: str) -> dict:
    proc = run(["docker", "inspect", name])
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()[:300]}
    cfg = json.loads(proc.stdout)[0]
    host_cfg = cfg.get("HostConfig", {})
    return {
        "image": cfg.get("Config", {}).get("Image"),
        "nano_cpus": host_cfg.get("NanoCpus"),
        "memory_bytes": host_cfg.get("Memory"),
        "memory_swap": host_cfg.get("MemorySwap"),
    }


def container_usage() -> list:
    proc = run(
        [
            "docker",
            "stats",
            "--no-stream",
            "--format",
            "{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}",
        ]
    )
    rows = []
    for line in proc.stdout.splitlines():
        if "|" in line:
            name, cpu, mem = line.split("|", 2)
            if name.startswith("aura-"):
                rows.append({"name": name, "cpu_pct": cpu, "mem_usage": mem})
    return rows


def cgroup_ollama() -> dict:
    cmd = (
        "cat /sys/fs/cgroup/cpu.max; echo ---; "
        "cat /sys/fs/cgroup/memory.max; echo ---; "
        "cat /sys/fs/cgroup/memory.current; echo ---; "
        "cat /sys/fs/cgroup/memory.swap.current; echo ---; "
        "cat /sys/fs/cgroup/memory.events; echo ---; "
        "cat /sys/fs/cgroup/cpu.stat"
    )
    proc = run(["docker", "exec", "aura-ollama", "sh", "-c", cmd])
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()[:300]}
    parts = [p.strip() for p in proc.stdout.split("---")]
    quota, period = (int(x) for x in parts[0].split())
    events = dict(l.split() for l in parts[4].splitlines() if len(l.split()) == 2)
    stats = dict(l.split() for l in parts[5].splitlines() if len(l.split()) == 2)
    return {
        "cpu_max": parts[0],
        "effective_cores": quota / period,
        "memory_max_bytes": int(parts[1]),
        "memory_current_bytes": int(parts[2]),
        "swap_current_bytes": int(parts[3]),
        "events": events,
        "cpu_stat": stats,
    }


def ollama_state() -> dict:
    version = run(["docker", "exec", "aura-ollama", "ollama", "--version"])
    ps = run(["docker", "exec", "aura-ollama", "ollama", "ps"])
    models = run(["docker", "exec", "aura-ollama", "ollama", "list"])
    return {
        "version": version.stdout.strip(),
        "resident_models": ps.stdout.strip(),
        "available_models": models.stdout.strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", action="store_true")
    args = parser.parse_args()

    total, _used, free = shutil.disk_usage(str(REPO))
    record = {
        "captured_utc": datetime.now(UTC).isoformat(),
        "evidence_class": "TARGET" if args.target else "DEV (not representative)",
        "hostname": platform.node(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": __import__("os").cpu_count(),
        "host_memory": host_memory(),
        "disk": {
            "total_gb": round(total / 2**30, 2),
            "free_gb": round(free / 2**30, 2),
        },
        "compose": compose_limits(),
        "containers": {
            name: container_limits(name)
            for name in ("aura-ollama", "aura-backend", "aura-litellm", "aura-postgres", "aura-redis")
        },
        "container_usage": container_usage(),
        "ollama_cgroup": cgroup_ollama(),
        "ollama_state": ollama_state(),
        "expected_target": "Contabo VPS 4 — 4 vCPU / 8 GB RAM",
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"hardware_{platform.node()}.json"
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    print(f"\nWrote {out.relative_to(REPO)}")
    if not args.target:
        print("NOTE: dev-box evidence only. Re-run with --target on the Contabo core.")


if __name__ == "__main__":
    main()
