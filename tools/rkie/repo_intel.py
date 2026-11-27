#!/usr/bin/env python3
"""CLI for IAM repository intelligence (Phase 2 features).

All commands are deterministic, local-first and model-independent. --json is
the stable machine-readable interface used by the agent API.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from intel_core import (
    ROOT,
    HybridSearch,
    build_code_index,
    candidate_files,
    change_impact,
    dead_symbols,
    git_blame,
    git_diff,
    git_history,
    import_cycles,
    load_code_index,
    rel,
    sha256,
    symbol_report,
    changelog,
)

MEMORY_DIR = ROOT / "tools" / "rkie" / "notes" / "memory"
BENCH_PATH = ROOT / "tools" / "rkie" / "index" / "benchmark.json"


def emit(payload: object, as_json: bool) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True) if as_json else payload)


def cmd_build(args: argparse.Namespace) -> int:
    from index_migrations import apply

    migration = apply()
    code_path = build_code_index()
    search_path = HybridSearch().build()
    from semantic import build as build_semantic

    semantic_path = build_semantic()
    apply()  # refresh recorded semantic schema version
    print(f"Schema version: {migration['schema_version']}")
    print(f"Code index: {rel(code_path)}")
    print(f"Search index: {rel(search_path)}")
    print(f"Semantic index: {rel(semantic_path)}")
    return 0


def cmd_symbol(args: argparse.Namespace) -> int:
    if not load_code_index():
        build_code_index()
    emit(symbol_report(args.name), args.json)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    engine = HybridSearch()
    if not engine.db_path.is_file():
        engine.build()
    emit(engine.search(args.query, args.limit), args.json)
    return 0


def cmd_impact(args: argparse.Namespace) -> int:
    if not load_code_index():
        build_code_index()
    emit(change_impact(args.files), args.json)
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    index = load_code_index()
    if not index:
        build_code_index()
        index = load_code_index()
    source_files = [p for p in index.get("files", {}) if p.startswith("backend/app/")]
    test_files = {p for p in index.get("files", {}) if "/tests/" in p}
    missing_tests = []
    for path in source_files:
        stem = Path(path).stem
        if not any(stem in test or test.endswith("/" + stem + ".py") for test in test_files):
            missing_tests.append(path)
    docs_with_broken_refs = []
    for doc in candidate_files({".md"}):
        text = doc.read_text(encoding="utf-8", errors="replace")
        for target in set(__import__("re").findall(r"`((?:backend|frontend|sdk|infra|tools)/[^`\s]+\.[a-z]+)`", text)):
            if not (ROOT / target).exists():
                docs_with_broken_refs.append({"doc": rel(doc), "target": target})
    payload = {
        "import_cycles": import_cycles(index),
        "dead_symbol_candidates": dead_symbols(index)[:50],
        "source_files_without_tests": missing_tests[:50],
        "broken_documentation_references": docs_with_broken_refs[:50],
        "counts": {
            "source_files": len(source_files),
            "test_files": len(test_files),
            "routes": len(index.get("routes", [])),
            "models": len(index.get("models", [])),
        },
    }
    emit(payload, args.json)
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    emit(git_history(args.query, args.limit, args.regex), args.json)
    return 0


def cmd_git(args: argparse.Namespace) -> int:
    if args.git_command == "blame":
        emit({"blame": git_blame(args.path, args.line)}, args.json)
    elif args.git_command == "diff":
        emit({"diff": git_diff(args.from_ref, args.to_ref)}, args.json)
    else:
        emit({"changelog": changelog(args.from_ref, args.to_ref)}, args.json)
    return 0


def cmd_memory(args: argparse.Namespace) -> int:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = MEMORY_DIR / f"{args.topic}.json"
    if args.memory_command == "record":
        if path.exists() and not args.force:
            print(f"Note exists: {rel(path)} (use --force to replace)")
            return 1
        payload = {
            "topic": args.topic,
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "question": args.question or "",
            "files": {f: sha256(ROOT / f) for f in args.files if (ROOT / f).is_file()},
            "evidence": args.evidence or [],
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"Recorded {rel(path)}")
        return 0
    if args.memory_command == "verify":
        if not path.exists():
            print(f"No note for topic: {args.topic}")
            return 2
        note = json.loads(path.read_text(encoding="utf-8"))
        stale = []
        for file, digest in note.get("files", {}).items():
            current = sha256(ROOT / file) if (ROOT / file).is_file() else None
            if current != digest:
                stale.append(file)
        emit({"topic": args.topic, "fresh": not stale, "stale_files": stale}, args.json)
        return 0 if not stale else 1
    emit([p.stem for p in sorted(MEMORY_DIR.glob("*.json"))], args.json)
    return 0


BENCHMARKS = [
    ("modelrouter", "filename", "backend/app/api/routes/modelrouter.py"),
    ("IntelligenceRouter", "symbol", "backend/app/services/intel_router_service.py"),
    ("/api/v1/memory", "fts", "backend/app/api/routes/memory.py"),
    ("OD-46", "fts", "IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md"),
    ("KnowledgeItem", "symbol", "backend/app/models/memory.py"),
]


def cmd_benchmark(args: argparse.Namespace) -> int:
    # Measure the deterministic core; neural re-ranking is model-latency bound.
    import os

    os.environ["IAM_NO_NEURAL"] = "1"
    engine = HybridSearch()
    if not engine.db_path.is_file():
        engine.build()
    index = load_code_index()
    rows = []
    for query, kind, expected in BENCHMARKS:
        start = time.perf_counter()
        results = engine.search(query, 20)
        latency = (time.perf_counter() - start) * 1000
        paths = [r["path"] for r in results]
        hit = expected in paths
        rank = paths.index(expected) + 1 if hit else 0
        rows.append({
            "query": query, "kind": kind, "expected": expected,
            "hit": hit, "rank": rank, "latency_ms": round(latency, 3),
        })
    hits = sum(r["hit"] for r in rows)
    payload = {
        "queries": len(rows),
        "hits": hits,
        "recall_at_20": round(hits / len(rows), 3),
        "mean_latency_ms": round(statistics.mean(r["latency_ms"] for r in rows), 3),
        "p95_latency_ms": round(sorted(r["latency_ms"] for r in rows)[-1], 3),
        "rows": rows,
    }
    BENCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    BENCH_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else
          f"recall@20={payload['recall_at_20']} mean={payload['mean_latency_ms']}ms")
    return 0 if hits == len(rows) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("build", help="build AST and FTS indexes").set_defaults(func=cmd_build)

    p = sub.add_parser("symbol", help="definition, callers, importers, routes")
    p.add_argument("name")
    p.set_defaults(func=cmd_symbol)

    p = sub.add_parser("search", help="hybrid exact/FTS/fuzzy search")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("impact", help="change-impact report")
    p.add_argument("files", nargs="+")
    p.set_defaults(func=cmd_impact)

    sub.add_parser("health", help="cycles, dead code, missing tests, broken docs").set_defaults(func=cmd_health)

    p = sub.add_parser("history", help="git pickaxe search")
    p.add_argument("query")
    p.add_argument("--regex", action="store_true")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_history)

    p = sub.add_parser("git", help="blame / diff / changelog")
    p.add_argument("git_command", choices=["blame", "diff", "changelog"])
    p.add_argument("--path")
    p.add_argument("--line", type=int, default=1)
    p.add_argument("--from-ref", default="HEAD~1")
    p.add_argument("--to-ref", default="HEAD")
    p.set_defaults(func=cmd_git)

    p = sub.add_parser("memory", help="investigation memory")
    p.add_argument("memory_command", choices=["record", "verify", "list"])
    p.add_argument("topic", nargs="?")
    p.add_argument("--files", nargs="*", default=[])
    p.add_argument("--question")
    p.add_argument("--evidence", nargs="*", default=[])
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_memory)

    sub.add_parser("benchmark", help="search recall/latency benchmark").set_defaults(func=cmd_benchmark)

    # Accept --json before or after the subcommand.
    for command_parser in sub.choices.values():
        command_parser.add_argument("--json", action="store_true", dest="json_sub")

    args = parser.parse_args()
    args.json = bool(getattr(args, "json", False) or getattr(args, "json_sub", False))
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
