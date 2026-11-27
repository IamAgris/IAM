#!/usr/bin/env python3
"""Generate or verify the IAM OpenAPI snapshot against the live FastAPI app.

The snapshot is IAM_OPENAPI.json at the repository root. Use --check in CI to
detect drift; use --update deliberately when a contract change is approved.

This script is independent of the RKIE search toolkit and uses only the project's
own FastAPI app as the source of truth.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "IAM_OPENAPI.json"


def load_live_spec() -> dict:
    backend = str(ROOT / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)
    from app.main import app  # noqa: E402  (import needs sys.path prepared)

    return app.openapi()


def render(spec: dict) -> str:
    return json.dumps(spec, indent=2, ensure_ascii=False) + "\n"


def check(spec: dict) -> int:
    if not SNAPSHOT.is_file():
        print(f"ERROR: snapshot missing: {SNAPSHOT}", file=sys.stderr)
        return 2

    try:
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot parse snapshot: {exc}", file=sys.stderr)
        return 2

    live_paths = set(spec.get("paths", {}))
    snapshot_paths = set(snapshot.get("paths", {}))
    missing = sorted(live_paths - snapshot_paths)
    extra = sorted(snapshot_paths - live_paths)

    live_schemas = len(spec.get("components", {}).get("schemas", {}))
    snapshot_schemas = len(snapshot.get("components", {}).get("schemas", {}))

    print(
        "OpenAPI drift check: live paths={0}, snapshot paths={1}; "
        "live schemas={2}, snapshot schemas={3}".format(
            len(live_paths), len(snapshot_paths), live_schemas, snapshot_schemas
        )
    )

    if missing:
        print(f"Paths declared in code but absent from snapshot ({len(missing)}):")
        for path in missing[:25]:
            print(f"  + {path}")
        if len(missing) > 25:
            print(f"  ... and {len(missing) - 25} more")
    if extra:
        print(f"Paths in snapshot but no longer declared in code ({len(extra)}):")
        for path in extra[:25]:
            print(f"  - {path}")
        if len(extra) > 25:
            print(f"  ... and {len(extra) - 25} more")
    if live_schemas != snapshot_schemas:
        print(
            f"Schema count differs by {live_schemas - snapshot_schemas:+d}; "
            "review with --update only after an approved contract change."
        )

    if missing or extra:
        print("RESULT: DRIFT. Regenerate with --update if the change is intentional.")
        return 1
    if live_schemas != snapshot_schemas:
        print("RESULT: DRIFT (schemas). Review the snapshot before approving.")
        return 1
    print("RESULT: OK")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="compare live app with snapshot")
    group.add_argument("--update", action="store_true", help="write the root snapshot")
    group.add_argument("--output", metavar="PATH", help="write generated spec to PATH")
    args = parser.parse_args()

    spec = load_live_spec()

    if args.check:
        return check(spec)
    if args.update:
        SNAPSHOT.write_text(render(spec), encoding="utf-8", newline="\n")
        print(f"Updated {SNAPSHOT}")
        return 0

    target = Path(args.output)
    target.write_text(render(spec), encoding="utf-8", newline="\n")
    print(f"Wrote {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
