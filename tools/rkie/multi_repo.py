#!/usr/bin/env python3
"""Multi-repository discovery with explicit authority labels.

External research is searchable but is never mixed into authoritative
implementation evidence. This keeps IAM's own code, its SDKs and external
recommendations distinguishable.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from intel_core import ROOT, INDEX_DIR, HybridSearch, candidate_files, rel, sha256

REGISTRY = ROOT / "tools" / "rkie" / "config" / "repositories.json"


def registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def files_for(name: str | None = None) -> list[dict]:
    repos = registry()["repositories"]
    result = []
    for repo in repos:
        if name and repo["name"] != name:
            continue
        prefix = "" if repo["path"] == "." else repo["path"] + "/"
        for path in candidate_files():
            rpath = rel(path)
            if rpath.startswith(prefix):
                result.append({
                    "repository": repo["name"],
                    "authority": repo["authority"],
                    "role": repo["role"],
                    "path": rpath,
                    "sha256": sha256(path),
                })
    return result


def search(query: str, repo: str | None = None, limit: int = 20) -> list[dict]:
    engine = HybridSearch()
    if not engine.db_path.is_file():
        engine.build()
    allowed = {f["path"] for f in files_for(repo)}
    results = [r for r in engine.search(query, limit * 3) if r["path"] in allowed]
    by_path = {f["path"]: f for f in files_for(repo)}
    for result in results:
        info = by_path.get(result["path"], {})
        result["repository"] = info.get("repository", "unknown")
        result["authority"] = info.get("authority", "unknown")
    return results[:limit]


def external_notes() -> list[dict]:
    return [f for f in files_for("iam-research-notes") if f["authority"] == "external"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["list", "files", "search", "external"])
    parser.add_argument("--repo")
    parser.add_argument("--query")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "list":
        payload = registry()
    elif args.command == "files":
        payload = {"count": len(files_for(args.repo)), "files": files_for(args.repo)}
    elif args.command == "search":
        if not args.query:
            parser.error("search requires --query")
        payload = {"query": args.query, "results": search(args.query, args.repo, args.limit)}
    else:
        payload = {"count": len(external_notes()), "notes": external_notes()}

    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
