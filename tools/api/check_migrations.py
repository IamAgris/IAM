#!/usr/bin/env python3
"""Detect duplicate numeric prefixes in backend SQL migrations.

The audit found two files numbered 009. Alembic versions and numbered SQL
scripts must be unambiguous; this is a fast, dependency-free gate.
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "backend" / "app" / "db" / "migrations"
NUMBERED = re.compile(r"^(\d+)_.*\.sql$")


def main() -> int:
    groups: dict[str, list[str]] = defaultdict(list)
    for path in sorted(MIGRATIONS.glob("*.sql")):
        match = NUMBERED.match(path.name)
        if match:
            groups[match.group(1)].append(path.name)

    duplicates = {n: names for n, names in groups.items() if len(names) > 1}
    print(f"Numbered SQL migrations: {sum(len(v) for v in groups.values())} files, {len(groups)} distinct numbers")
    if not duplicates:
        print("RESULT: OK")
        return 0

    for number in sorted(duplicates, key=int):
        print(f"Duplicate prefix {number}: {', '.join(sorted(duplicates[number]))}")
    print("RESULT: DUPLICATE MIGRATION NUMBERS")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
