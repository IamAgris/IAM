#!/usr/bin/env python3
"""Run strict mypy over the whole backend and ratchet existing errors.

The repository currently has thousands of pre-existing strict-typing errors.
This gate records them as a normalized baseline and fails only when a NEW
error (or a new occurrence of a known error) appears. Fixing errors always
passes; regenerate the baseline deliberately after a reduction.

Usage:
    python tools/quality/check_mypy_ratchet.py
    python tools/quality/check_mypy_ratchet.py --update-baseline
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
CONFIG = BACKEND / "mypy-full.ini"
LEGACY_BASELINE = BACKEND / "mypy-baseline.json"
ERROR = re.compile(r"^(.+?):(\d+): error: (.*)$")


def baseline_path() -> Path:
    """Select the baseline recorded for this Python version.

    mypy's error set differs between interpreter versions, so CI (3.12) and a
    developer host (e.g. 3.15) each keep their own baseline.
    """
    versioned = BACKEND / "mypy-baseline-{}.{}.json".format(
        sys.version_info.major, sys.version_info.minor)
    return versioned if versioned.is_file() else LEGACY_BASELINE


BASELINE = baseline_path()


def normalized_errors(output: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for line in output.splitlines():
        match = ERROR.match(line)
        if match:
            counts[f"{match.group(1)}: error: {match.group(3)}"] += 1
    return counts


def run_mypy() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", str(CONFIG)],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        errors="replace",
    )
    return result.stdout + result.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()
    if not CONFIG.is_file():
        print(f"ERROR: missing config {CONFIG}", file=sys.stderr)
        return 2

    output = run_mypy()
    current = normalized_errors(output)

    if args.update_baseline:
        import json

        BASELINE.write_text(
            json.dumps({"version": 1, "counts": dict(current)}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        file_count = sum(1 for _ in BACKEND.rglob("*.py"))
        print(f"Baseline written: {sum(current.values())} errors across {file_count} files")
        return 0

    if not BASELINE.is_file():
        print(f"ERROR: no baseline at {BASELINE}; run with --update-baseline once", file=sys.stderr)
        return 2

    import json

    baseline = Counter(json.loads(BASELINE.read_text(encoding="utf-8"))["counts"])
    new = current - baseline
    fixed = baseline - current

    print(
        f"Strict mypy ratchet: {sum(current.values())} errors "
        f"(baseline {sum(baseline.values())}, new {sum(new.values())}, fixed {sum(fixed.values())})"
    )
    for signature, count in list(new.items())[:25]:
        print(f"  NEW x{count}: {signature}")
    if sum(new.values()) > 25:
        print(f"  ... and {sum(new.values()) - 25} more new errors")

    if new:
        print("RESULT: DRIFT. Fix the new errors, then regenerate the baseline if reduction is intentional.")
        return 1
    print("RESULT: OK (no new strict-typing errors)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
