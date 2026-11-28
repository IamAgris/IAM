#!/usr/bin/env python3
"""Run the deterministic quality gates locally, in the same order as CI.

This is a local simulation, not GitHub Actions. It deliberately excludes the
compose-based acceptance job, which needs a live stack and runner ports.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

STEPS: list[tuple[str, list[str], Path | None]] = [
    ("lint", [sys.executable, "-m", "ruff", "check", "backend"], ROOT),
    ("types-strict", [sys.executable, "-m", "mypy", "--config-file", "mypy.ini"], ROOT / "backend"),
    ("types-ratchet", [sys.executable, "tools/quality/check_mypy_ratchet.py"], ROOT),
    ("workflows", [sys.executable, "tools/quality/check_workflows.py"], ROOT),
    ("repo-intel", [sys.executable, "-m", "pytest", "tools/rkie/tests", "-q"], ROOT),
    ("openapi", [sys.executable, "tools/api/print_openapi.py", "--check"], ROOT),
    ("migrations", [sys.executable, "tools/api/check_migrations.py"], ROOT),
    ("benchmark", [sys.executable, "tools/rkie/repo_intel.py", "benchmark"], ROOT),
    ("sdk-python", [sys.executable, "-m", "pytest", "tests", "-q"], ROOT / "sdk" / "python"),
    ("backend-tests", [sys.executable, "-m", "pytest", "tests", "-q",
                       "--cov=app", "--cov-report=term:skip-covered", "--cov-fail-under=60"],
     ROOT / "backend"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", nargs="*", help="run only named steps")
    args = parser.parse_args()

    failures = []
    for name, command, cwd in STEPS:
        if args.only and name not in args.only:
            continue
        started = time.perf_counter()
        result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, errors="replace")
        elapsed = (time.perf_counter() - started) * 1000
        status = "PASS" if result.returncode == 0 else "FAIL"
        print(f"[{status}] {name} ({elapsed:.0f} ms)")
        if result.returncode != 0:
            failures.append(name)
            tail = (result.stdout + result.stderr).strip().splitlines()[-12:]
            for line in tail:
                print("    " + line)

    print(f"\nLOCAL CI: {len(STEPS) - len(failures)} passed, {len(failures)} failed")
    if failures:
        print("Failed: " + ", ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
