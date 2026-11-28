#!/usr/bin/env python3
"""Polling background indexer with file-change detection.

No OS file-watcher dependency: compares SHA-256 hashes of the same candidate
file set used by the search toolkit and rebuilds derived indexes only when
files actually changed. ``--once`` is CI-friendly; without it the process
loops until stopped.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from intel_core import INDEX_DIR, ROOT, candidate_files, rel, sha256

STATE_PATH = INDEX_DIR / "watch-state.json"


def snapshot() -> dict[str, str]:
    return {rel(path): sha256(path) for path in candidate_files()}


def read_state() -> dict:
    if STATE_PATH.is_file():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"version": 1, "files": {}}


def rebuild() -> None:
    from repo_intel import cmd_build

    cmd_build(argparse.Namespace(json=False))


def cycle() -> dict:
    current = snapshot()
    state = read_state()
    previous = state.get("files", {})
    changed = sorted(
        path for path, digest in current.items()
        if previous.get(path) != digest
    )
    removed = sorted(set(previous) - set(current))
    if changed or removed or not previous:
        rebuild()
        state = {
            "version": 1,
            "last_run": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "files": current,
        }
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "checked": len(current),
        "changed": changed,
        "removed": removed,
        "rebuilt": bool(changed or removed or not previous),
    }


def watch_os(interval: int) -> None:
    """OS-level file watching via watchdog; falls back to polling if absent."""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        print("watchdog is not installed; use polling mode (default)")
        return

    state = {"last": 0.0}

    class Handler(FileSystemEventHandler):
        def on_any_event(self, event):
            if event.is_directory:
                return
            now = time.time()
            if now - state["last"] < max(1, interval):
                return
            state["last"] = now
            result = cycle()
            print(f"watch-os: rebuilt={result['rebuilt']} changed={len(result['changed'])}")

    observer = Observer()
    observer.schedule(
        Handler(), str(ROOT), recursive=True,
        patterns=["*.py", "*.ts", "*.tsx", "*.md", "*.sql", "*.json", "*.yaml", "*.yml", "*.ps1"],
        ignore_patterns=["*node_modules*", "*.next*", "*__pycache__*"],
    )
    observer.start()
    print("Watching repository with watchdog; Ctrl+C to stop")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch-os", action="store_true", help="use watchdog OS events")
    parser.add_argument("--once", action="store_true", help="run one check and exit")
    parser.add_argument("--interval", type=int, default=30, help="seconds between checks")
    parser.add_argument("--max-cycles", type=int, default=0, help="0 = unlimited")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.watch_os:
        watch_os(args.interval)
        return 0

    cycles = 0
    while True:
        result = cycle()
        cycles += 1
        print(json.dumps(result, sort_keys=True) if args.json else
              f"cycle {cycles}: checked={result['checked']} rebuilt={result['rebuilt']}")
        if args.once or (args.max_cycles and cycles >= args.max_cycles):
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
