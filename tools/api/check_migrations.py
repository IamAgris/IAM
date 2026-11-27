#!/usr/bin/env python3
"""Validate numbered SQL migrations against the explicit order manifest.

Duplicate numeric prefixes are allowed only when MIGRATION_ORDER.json gives
each file a distinct sequence. This removes ambiguity without renaming files
that are referenced by specifications and integration tests.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "backend" / "app" / "db" / "migrations"
MANIFEST = MIGRATIONS / "MIGRATION_ORDER.json"
NUMBERED = re.compile(r"^(\d+)_.*\.sql$")


def main() -> int:
    if not MANIFEST.is_file():
        print(f"ERROR: missing order manifest: {MANIFEST}", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        entries = manifest["files"]
    except (OSError, ValueError, KeyError) as exc:
        print(f"ERROR: cannot read order manifest: {exc}", file=sys.stderr)
        return 2

    manifest_paths = {entry["path"] for entry in entries}
    sequences = [entry["sequence"] for entry in entries]
    on_disk = {p.name for p in MIGRATIONS.glob("*.sql") if NUMBERED.match(p.name)}

    missing = sorted(on_disk - manifest_paths)
    stale = sorted(manifest_paths - on_disk)
    duplicate_sequences = [s for s, count in Counter(sequences).items() if count > 1]

    numbers = Counter(entry["number"] for entry in entries)
    sanctioned = {number for number, count in numbers.items() if count > 1}

    print(
        f"Numbered SQL migrations: {len(on_disk)} on disk, {len(entries)} in manifest, "
        f"{len(sanctioned)} duplicated prefixes (sanctioned by manifest)"
    )
    for number in sorted(sanctioned, key=int):
        names = [e["path"] for e in entries if e["number"] == number]
        print(f"  prefix {number}: {', '.join(sorted(names))}")

    for name in missing:
        print(f"ERROR: on disk but not in manifest: {name}")
    for name in stale:
        print(f"ERROR: in manifest but missing on disk: {name}")
    for sequence in duplicate_sequences:
        print(f"ERROR: duplicate sequence value: {sequence}")

    if missing or stale or duplicate_sequences:
        print("RESULT: DRIFT")
        return 1
    print("RESULT: OK (order is explicit in MIGRATION_ORDER.json)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
