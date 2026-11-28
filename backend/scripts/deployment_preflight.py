"""CLI deployment preflight.

Usage:  python scripts/deployment_preflight.py
Exit code 1 means one or more blockers remain.
"""

import sys

from app.services.deployment_preflight import check_deployment


def main() -> int:
    report = check_deployment()
    for check in report["checks"]:
        marker = {"ok": "OK   ", "blocker": "BLOCK", "warning": "WARN "}[check["status"]]
        # codeql[py/clear-text-logging-sensitive-data] check_deployment() returns redacted status text and env-var names only.
        print(f"[{marker}] {check['name']}: {check['detail']}")
    print()
    print(f"ready={report['ready']}")
    if report["blockers"]:
        print("blockers: " + ", ".join(report["blockers"]))
    if report["warnings"]:
        print("warnings: " + ", ".join(report["warnings"]))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
