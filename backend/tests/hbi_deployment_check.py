"""Document 26 (OD-45): report deployment readiness in any environment.

Default run is informational (exit 0). Pass --strict to fail when blockers
remain, for use as a deployment precondition.
"""

import asyncio
import sys

from app.services.hbi import HBIService


async def main(strict: bool) -> int:
    service = HBIService()
    result = await service.deployment_readiness()
    print(f"ready: {result['ready']}")
    for blocker in result["blockers"]:
        print(f"  BLOCKER {blocker}")
    for key, value in result["checks"].items():
        print(f"  {key}: {value}")
    if result["ready"]:
        print("HBI DEPLOYMENT READY")
        return 0
    print("HBI DEPLOYMENT NO-GO", file=sys.stderr)
    return 1 if strict else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main("--strict" in sys.argv)))
