#!/usr/bin/env python3
"""Stable, model-independent repository intelligence interface for IAM agents.

Qwen2.5:3B (or any other model) may call these functions through the CLI with
--json. Indexing, ranking and verification remain deterministic tools; the
model never parses source itself.
"""
from __future__ import annotations

import argparse
import json
import re

from intel_core import (
    HybridSearch,
    change_impact,
    git_history,
    load_code_index,
    symbol_report,
)
from repo_intel import MEMORY_DIR, cmd_benchmark, cmd_health, cmd_memory
from types import SimpleNamespace


def search(query: str, limit: int = 10) -> dict:
    engine = HybridSearch()
    if not engine.db_path.is_file():
        engine.build()
    return {"query": query, "results": engine.search(query, limit)}


def symbol(name: str) -> dict:
    index = load_code_index()
    return symbol_report(name, index)


def impact(files: list[str]) -> dict:
    return change_impact(files, load_code_index())


def history(query: str, limit: int = 10) -> dict:
    return {"query": query, "commits": git_history(query, limit)}


def remember(topic: str, files: list[str], question: str = "") -> dict:
    args = SimpleNamespace(
        topic=topic, memory_command="record", files=files, question=question,
        evidence=[], force=True, json=True,
    )
    cmd_memory(args)
    path = MEMORY_DIR / f"{topic}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def verify_memory(topic: str) -> dict:
    args = SimpleNamespace(topic=topic, memory_command="verify", json=True)
    return _capture(lambda: cmd_memory(args))


def health() -> dict:
    return _capture(lambda: cmd_health(SimpleNamespace(json=True)))


def benchmark() -> dict:
    _capture(lambda: cmd_benchmark(SimpleNamespace(json=True)))
    from repo_intel import BENCH_PATH
    return json.loads(BENCH_PATH.read_text(encoding="utf-8"))


def _capture(func) -> dict:
    import contextlib
    import io

    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        func()
    return json.loads(stream.getvalue())


def plan(question: str) -> dict:
    """Choose a search strategy without executing expensive retrieval."""
    text = question.lower()
    if re.search(r"\b(who calls|usages|references|impact|break|affect)\b", text):
        strategy = ["symbol", "impact"]
    elif re.search(r"\b(when|history|introduced|deleted|previous)\b", text):
        strategy = ["history"]
    elif re.search(r"\b(explain|architecture|spec|decision|requirement|gap)\b", text):
        strategy = ["docs", "symbol", "health"]
    elif re.search(r"\b(error|bug|fail|exception)\b", text):
        strategy = ["search", "history", "tests"]
    elif re.search(r"\b(file|filename|where is)\b", text):
        strategy = ["search"]
    else:
        strategy = ["search", "symbol"]
    return {"question": question, "strategy": strategy}


OPERATIONS = {
    "search": lambda a: search(a["query"], int(a.get("limit", 10))),
    "symbol": lambda a: symbol(a["name"]),
    "impact": lambda a: impact(a["files"]),
    "history": lambda a: history(a["query"], int(a.get("limit", 10))),
    "remember": lambda a: remember(a["topic"], a["files"], a.get("question", "")),
    "verify_memory": lambda a: verify_memory(a["topic"]),
    "health": lambda a: health(),
    "benchmark": lambda a: benchmark(),
    "plan": lambda a: plan(a["question"]),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=sorted(OPERATIONS))
    parser.add_argument("--input", help="JSON object with operation arguments")
    args = parser.parse_args()
    payload = json.loads(args.input) if args.input else {}
    print(json.dumps(OPERATIONS[args.operation](payload), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
