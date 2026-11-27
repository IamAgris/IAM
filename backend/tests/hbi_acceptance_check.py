"""Document 26 (OD-45): CI acceptance gate for Human Behaviour Intelligence.

Runs the §11.7 acceptance gates against a fresh in-memory HBI service.
Exit code 0 means all gates passed; any failure blocks promotion.
"""

import asyncio
import sys

from app.services.hbi import HBIService
from app.services.hbi.schemas import AnalysisRequest, KnowledgeRecordInput, EvidenceItem


async def main() -> int:
    service = HBIService()
    await service.add_record(KnowledgeRecordInput(
        claim="Community trust increased after the programme",
        epistemic_type="observation",
        evidence=[EvidenceItem(
            source_id="ci-source", source_type="peer_reviewed_journal",
            licence="cc-by", permitted_purpose="research",
        )],
    ))
    await service.analyse(AnalysisRequest(question="trust", purpose="research"))
    result = await service.run_acceptance()
    for gate in result["gates"]:
        status = "PASS" if gate["passed"] else "FAIL"
        print(f"  {status} {gate['gate']}")
    if result["passed"]:
        print(f"HBI ACCEPTANCE PASSED ({result['count']} gates)")
        return 0
    print(f"HBI ACCEPTANCE FAILED: {result['failed']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
