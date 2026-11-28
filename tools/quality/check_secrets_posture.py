#!/usr/bin/env python3
"""Verify deployment secrets posture without reading secret values.

OD-07 requires SOPS-encrypted env files + Docker secrets; OD-58 adds an
optional Infisical source with Docker secrets as fallback. This check only
looks for structural problems: placeholder defaults for sensitive fields in
Compose, missing SOPS configuration, and secret-looking literals in tracked
example files. It never prints a value.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "docker-compose.yml"
SOPS_CONFIG = ROOT / ".sops.yaml"
EXAMPLE_ENV = ROOT / ".env.example"

SECRET_SUFFIXES = ("_PASSWORD", "_SECRET", "_KEY", "_TOKEN")
PLACEHOLDER = re.compile(r"change-me|changeme|replace|your[-_]|example", re.IGNORECASE)


def _is_secret_key(key: str) -> bool:
    return key.upper().endswith(SECRET_SUFFIXES) and not key.upper().endswith(
        ("_ENV", "_FILE", "_PATH", "_TOKENS")
    )


def _compose_placeholders(data: Dict[str, Any]) -> List[str]:
    """Local placeholder defaults are expected; report them as warnings."""
    warnings: List[str] = []
    for name, spec in (data.get("services") or {}).items():
        if not isinstance(spec, dict):
            continue
        for key, value in (spec.get("environment") or {}).items():
            if not _is_secret_key(str(key)):
                continue
            match = re.match(r"^\$\{[^:]+:-([^}]*)\}$", str(value))
            if match and PLACEHOLDER.search(match.group(1)):
                warnings.append(f"{name}.{key} has a local placeholder default")
    return warnings


def check() -> Dict[str, Any]:
    problems: List[str] = []
    warnings: List[str] = []
    try:
        data = yaml.safe_load(COMPOSE.read_text(encoding="utf-8")) or {}
        warnings.extend(_compose_placeholders(data))
    except (OSError, yaml.YAMLError) as exc:
        problems.append(f"cannot parse compose: {type(exc).__name__}")

    if not SOPS_CONFIG.is_file():
        problems.append("missing .sops.yaml (OD-07 SOPS configuration)")

    if EXAMPLE_ENV.is_file():
        for line in EXAMPLE_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if (
                _is_secret_key(key)
                and value.strip()
                and not PLACEHOLDER.search(value)
                and not value.strip().startswith("<")
            ):
                problems.append(f".env.example sets a non-placeholder value for {key}")

    return {"ok": not problems, "problems": problems, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = check()
    print(json.dumps(result, indent=2, sort_keys=True) if args.json else
          "\n".join([f"Secrets posture: {'OK' if result['ok'] else 'DRIFT'}"] +
                    [f"  - {p}" for p in result["problems"]] +
                    [f"  ~ {w}" for w in result["warnings"]]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
