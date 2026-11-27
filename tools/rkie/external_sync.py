#!/usr/bin/env python3
"""Offline synchronisation of registered external knowledge sources.

Copies metadata (path, hash, authority, role) from locally available external
repositories into a versioned index. No network calls: external content stays
labelled as external and never becomes authoritative implementation evidence.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from intel_core import INDEX_DIR, ROOT, rel, sha256
from multi_repo import registry

INDEX_PATH = INDEX_DIR / "external-knowledge.json"
TEXT_SUFFIXES = {".md", ".py", ".ts", ".tsx", ".json", ".yaml", ".yml", ".txt"}
SKIP = {"node_modules", ".git", ".next", "__pycache__"}


def collect() -> dict:
    sources = []
    for repo in registry()["repositories"]:
        if repo.get("authority") != "external":
            continue
        base = ROOT / repo["path"]
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if any(part in SKIP for part in path.relative_to(ROOT).parts):
                continue
            rpath = rel(path)
            sources.append({
                "path": rpath,
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "authority": "external",
                "role": repo["role"],
                "repository": repo["name"],
            })
    return {
        "version": 1,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sources": sources,
    }


def verify() -> dict:
    if not INDEX_PATH.is_file():
        return {"ok": False, "reason": "no external knowledge index; run --apply"}
    stored = {s["path"]: s["sha256"] for s in json.loads(INDEX_PATH.read_text(encoding="utf-8"))["sources"]}
    current = {s["path"]: s["sha256"] for s in collect()["sources"]}
    changed = sorted(p for p, digest in current.items() if stored.get(p) != digest)
    missing = sorted(set(stored) - set(current))
    return {
        "ok": not changed and not missing,
        "source_count": len(current),
        "changed": changed,
        "missing": missing,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.apply:
        payload = collect()
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        INDEX_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        payload = verify()

    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload)
    return 0 if payload.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
