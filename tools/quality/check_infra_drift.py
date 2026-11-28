#!/usr/bin/env python3
"""Detect infrastructure drift in docker-compose.yml before deployment.

Checks the structural contract that the stack relies on: required services,
health checks for core dependencies, and that every host bind mount actually
exists in the repository. Missing mounts are a common cause of a stack that
starts but runs with the wrong configuration (for example an unmounted
reverse-proxy config).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker-compose.yml"

REQUIRED_SERVICES = ("postgres", "redis", "litellm", "backend", "frontend")
HEALTHCHECK_SERVICES = ("postgres", "redis", "backend", "litellm")
REQUIRED_PATHS = (
    "infra/litellm/config.yaml",
    "infra/postgres/init",
)


def _bind_sources(spec: Dict[str, Any]) -> List[str]:
    sources: List[str] = []
    for volume in spec.get("volumes") or []:
        if isinstance(volume, str) and ":" in volume and not volume.startswith("//"):
            source = volume.split(":", 1)[0]
            if source and not source.startswith("/") and not source.startswith("$"):
                sources.append(source)
        elif isinstance(volume, dict):
            source = str(volume.get("source") or "")
            if source and not source.startswith("/"):
                sources.append(source)
    return sources


def check() -> Dict[str, Any]:
    problems: List[str] = []
    if not COMPOSE.is_file():
        return {"ok": False, "problems": [f"missing {COMPOSE.name}"]}

    try:
        data = yaml.safe_load(COMPOSE.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return {"ok": False, "problems": [f"invalid YAML: {exc}"]}

    services = data.get("services") or {}
    for name in REQUIRED_SERVICES:
        if name not in services:
            problems.append(f"required service missing: {name}")
    for name in HEALTHCHECK_SERVICES:
        if name in services and "healthcheck" not in services[name]:
            problems.append(f"healthcheck missing: {name}")

    for rel in REQUIRED_PATHS:
        if not (ROOT / rel).exists():
            problems.append(f"required infra path missing: {rel}")

    named_volumes = set((data.get("volumes") or {}).keys())
    seen: set[str] = set()
    for name, spec in services.items():
        if not isinstance(spec, dict):
            continue
        for source in _bind_sources(spec):
            if source in seen or source in named_volumes:
                continue
            seen.add(source)
            if not (ROOT / source).exists():
                problems.append(f"bind mount source missing: {source} (service {name})")

    return {
        "ok": not problems,
        "services": sorted(services),
        "checked_bind_mounts": len(seen),
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Infra drift: {'OK' if result['ok'] else 'DRIFT'}")
        for problem in result["problems"]:
            print(f"  - {problem}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
