#!/usr/bin/env python3
"""Persistent coordination for authorised IAM agents.

Agents claim investigation topics (and the files they touch) with a lease so
parallel workers do not duplicate expensive work or edit the same area. State
is local JSON, versioned and human-readable — no external service.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from intel_core import INDEX_DIR

STATE = INDEX_DIR / "agent-coordination.json"


def load() -> dict:
    if STATE.is_file():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {"version": 1, "claims": {}}


def save(state: dict) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def active_claims(state: dict) -> dict:
    now = time.time()
    return {
        topic: claim for topic, claim in state.get("claims", {}).items()
        if claim.get("expires_at", 0) > now
    }


def claim(topic: str, agent: str, files: list[str], ttl: int) -> dict:
    state = load()
    current = active_claims(state)
    if topic in current and current[topic]["agent"] != agent:
        return {"ok": False, "reason": "held_by_other_agent", "holder": current[topic]["agent"]}
    now = time.time()
    state.setdefault("claims", {})[topic] = {
        "agent": agent,
        "files": sorted(set(files)),
        "claimed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "expires_at": now + ttl,
    }
    save(state)
    return {"ok": True, "topic": topic, "agent": agent, "ttl_seconds": ttl}


def release(topic: str, agent: str) -> dict:
    state = load()
    current = active_claims(state)
    record = current.get(topic)
    if record and record["agent"] != agent:
        return {"ok": False, "reason": "held_by_other_agent", "holder": record["agent"]}
    state.get("claims", {}).pop(topic, None)
    save(state)
    return {"ok": True, "topic": topic}


def status(topic: str | None = None) -> dict:
    state = load()
    claims = active_claims(state)
    if topic:
        return {"topic": topic, "claim": claims.get(topic)}
    return {"count": len(claims), "claims": claims}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["claim", "release", "status"])
    parser.add_argument("topic", nargs="?")
    parser.add_argument("--agent", default="unknown")
    parser.add_argument("--files", nargs="*", default=[])
    parser.add_argument("--ttl", type=int, default=3600)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.command == "claim":
        if not args.topic:
            parser.error("claim requires a topic")
        payload = claim(args.topic, args.agent, args.files, args.ttl)
    elif args.command == "release":
        if not args.topic:
            parser.error("release requires a topic")
        payload = release(args.topic, args.agent)
    else:
        payload = status(args.topic)

    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else payload)
    return 0 if payload.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
