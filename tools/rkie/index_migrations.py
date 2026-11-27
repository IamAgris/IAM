#!/usr/bin/env python3
"""Versioned index schema migrations and integrity checks.

Indexes are caches, but a schema change must be explicit and recoverable. This
module records the schema version and rebuilds derived indexes when their
internal version no longer matches.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from intel_core import INDEX_DIR, ROOT, SEARCH_DB_PATH
from semantic import DB_PATH as SEMANTIC_DB, SCHEMA_VERSION as SEMANTIC_SCHEMA, schema_version

SCHEMA_PATH = INDEX_DIR / "INDEX_SCHEMA.json"
CURRENT_SCHEMA = 3


def read_schema() -> dict:
    if SCHEMA_PATH.is_file():
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return {"version": 0, "migrations": []}


def apply() -> dict:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    schema = read_schema()
    applied: list[str] = []

    if schema["version"] < 1:
        schema = {"version": 1, "migrations": ["initial index directory"]}
        applied.append("v1 initial index directory")

    if schema["version"] < 2:
        schema["version"] = 2
        schema["migrations"].append("fts5 + code-intel index contract")
        applied.append("v2 index contract")

    if schema["version"] < 3:
        schema["version"] = 3
        schema["migrations"].append("semantic TF-IDF index contract")
        applied.append("v3 semantic index contract")

    schema["fts5"] = {"path": str(SEARCH_DB_PATH.relative_to(ROOT).as_posix())}
    schema["semantic"] = {
        "path": str(SEMANTIC_DB.relative_to(ROOT).as_posix()),
        "expected_version": SEMANTIC_SCHEMA,
        "current_version": schema_version(),
    }
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"schema_version": schema["version"], "applied": applied, "schema": schema}


def check() -> dict:
    schema = read_schema()
    problems = []
    if schema.get("version", 0) != CURRENT_SCHEMA:
        problems.append(f"schema version {schema.get('version')} != {CURRENT_SCHEMA}")
    semantic = schema.get("semantic", {})
    if semantic.get("current_version") not in (0, semantic.get("expected_version")):
        problems.append("semantic index version mismatch; rebuild required")
    return {
        "schema_version": schema.get("version"),
        "expected_version": CURRENT_SCHEMA,
        "semantic_version": schema_version(),
        "problems": problems,
        "ok": not problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    payload = apply() if args.apply else check()
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload)
    return 0 if payload.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
