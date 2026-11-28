"""Document 26 (OD-45): report scientific validation state.

Informational by default. With --strict, exits non-zero while the validation
verdict is not `validated` — preventing synthetic or unverified data from
being presented as scientific evidence.
"""

import asyncio
import sys

from app.services.hbi import HBIService


async def main(strict: bool) -> int:
    service = HBIService()
    corpus = service.corpus_readiness()
    report = service.validation_report()
    print(f"licensed_records: {corpus['licensed_records']}")
    print(f"illustrative_fixtures: {corpus['illustrative_fixtures']}")
    print(f"verdict: {report['verdict']}")
    for blocker in report["blockers"]:
        print(f"  BLOCKER {blocker}")
    if report["verdict"] == "validated":
        print("HBI SCIENTIFIC VALIDATION PASSED")
        return 0
    print("HBI SCIENTIFIC VALIDATION NOT CLAIMED", file=sys.stderr)
    return 1 if strict else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main("--strict" in sys.argv)))
