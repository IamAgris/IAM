#!/usr/bin/env python3
"""Track and prioritise strict-typing debt from the mypy ratchet baseline."""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_VERSION = "mypy-baseline-{}.{}.json".format(sys.version_info.major, sys.version_info.minor)
BASELINE = ROOT / "backend" / _VERSION
if not BASELINE.is_file():
    BASELINE = ROOT / "backend" / "mypy-baseline.json"
HISTORY = ROOT / "tools" / "quality" / "index" / "mypy-debt.json"
FILE_RE = re.compile(r"^(.+?): error:")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--target", type=int, help="record a target error count")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    counts = json.loads(BASELINE.read_text(encoding="utf-8"))["counts"]
    by_file: dict[str, int] = {}
    by_code: dict[str, int] = {}
    for signature, count in counts.items():
        match = FILE_RE.match(signature)
        if match:
            by_file[match.group(1)] = by_file.get(match.group(1), 0) + count
        code = signature.rsplit("[", 1)[-1].rstrip("]")
        by_code[code] = by_code.get(code, 0) + count

    total = sum(counts.values())
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    history = json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.is_file() else {"entries": [], "target": None}
    if args.target is not None:
        history["target"] = args.target
    history["entries"].append({
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "errors": total,
        "files": len(by_file),
    })
    history["entries"] = history["entries"][-30:]
    HISTORY.write_text(json.dumps(history, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    payload = {
        "total_errors": total,
        "files_with_errors": len(by_file),
        "target": history.get("target"),
        "top_files": sorted(by_file.items(), key=lambda item: -item[1])[:args.top],
        "by_error_code": sorted(by_code.items(), key=lambda item: -item[1])[:10],
    }
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else
          f"{total} errors across {len(by_file)} files; top: {payload['top_files'][:3]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
