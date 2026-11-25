#!/usr/bin/env python3
"""Validate IAM instruction/output JSONL before a fine-tuning run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def validate(path: Path) -> int:
    if not path.is_file():
        raise SystemExit(f"Dataset file does not exist: {path}")

    count = 0
    errors: list[str] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            item: Any = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_number}: invalid JSON ({exc.msg})")
            continue

        if not isinstance(item, dict):
            errors.append(f"line {line_number}: expected a JSON object")
            continue

        for field in ("instruction", "output"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"line {line_number}: '{field}' must be a non-empty string")

        for field in ("input", "system"):
            if field in item and not isinstance(item[field], str):
                errors.append(f"line {line_number}: optional '{field}' must be a string")

        if not any(message.startswith(f"line {line_number}:") for message in errors):
            count += 1

    if errors:
        print(f"Found {len(errors)} dataset issue(s):")
        for error in errors[:100]:
            print(f"- {error}")
        if len(errors) > 100:
            print(f"- ... and {len(errors) - 100} more")
        raise SystemExit(1)

    if count == 0:
        raise SystemExit("Dataset contains no usable examples.")

    print(f"OK: {count} valid examples in {path}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()
    validate(args.dataset)


if __name__ == "__main__":
    main()
