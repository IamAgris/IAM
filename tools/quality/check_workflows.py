#!/usr/bin/env python3
"""Static validation of GitHub Actions workflows.

This cannot replace running Actions, but it catches broken script references,
invalid YAML, missing runners and hardcoded refs before a PR does.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
SCRIPT_REF = re.compile(r"(?:python|pwsh|\./)([A-Za-z0-9_./-]+\.(?:py|ps1|sh))")


def main() -> int:
    import yaml

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    problems: list[str] = []
    summaries: list[dict] = []
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            problems.append(f"{path.name}: invalid YAML: {exc}")
            continue
        jobs = data.get("jobs", {}) if isinstance(data, dict) else {}
        if not jobs:
            problems.append(f"{path.name}: no jobs")
        for name, job in jobs.items():
            if not isinstance(job, dict):
                problems.append(f"{path.name}:{name}: invalid job")
                continue
            if not job.get("runs-on") and not job.get("uses"):
                problems.append(f"{path.name}:{name}: missing runs-on")
            for step in job.get("steps", []):
                command = step.get("run", "") if isinstance(step, dict) else ""
                for reference in SCRIPT_REF.findall(command):
                    if not (ROOT / reference).is_file():
                        problems.append(f"{path.name}:{name}: missing script {reference}")
                if "ref: testing" in command:
                    problems.append(f"{path.name}:{name}: hardcoded ref: testing")
        summaries.append({"file": path.name, "jobs": sorted(jobs)})

    payload = {
        "workflows": len(summaries),
        "summaries": summaries,
        "problems": problems,
        "ok": not problems,
    }
    print(json.dumps(payload, indent=2, sort_keys=True) if args.json else
          f"workflows={len(summaries)} problems={len(problems)}")
    for problem in problems:
        print("  " + problem)
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
