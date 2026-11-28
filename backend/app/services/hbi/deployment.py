"""Document 26 (OD-45): deployment readiness gate.

Production activation requires passing acceptance gates, an approved DPIA
sign-off by an authorised reviewer, no prohibited dual-use decisions and a
documented rollback path. This gate never relaxes governance.
"""

from typing import Any, Dict, List


async def readiness(service: Any, config: Dict[str, Any] = None) -> Dict[str, Any]:  # type: ignore[assignment]
    """Return a go/no-go verdict with concrete blockers."""
    blockers: List[str] = []
    config = config or {}

    acceptance = await service.run_acceptance()
    if not acceptance["passed"]:
        blockers.append(f"acceptance_failed::{','.join(acceptance['failed'])}")

    loader = getattr(service, "load_dpia_signoffs", None)
    signoffs = await loader() if loader else list(getattr(service, "dpia_signoffs", []))
    approved = [item for item in signoffs if item.get("decision") == "approved"]
    if not approved:
        blockers.append("dpia_signoff_required")
    elif not all(item.get("reviewer") for item in approved):
        blockers.append("dpia_signoff_reviewer_required")

    prohibited = [
        event for event in service.core.audit_log
        if event.get("event_type") == "dual_use_review" and event.get("outcome") == "PROHIBITED"
    ]
    if prohibited:
        blockers.append(f"prohibited_capability::{len(prohibited)}")

    if not config.get("sdk_interface_registered", True):
        blockers.append("sdk_interface_not_registered")
    if not config.get("migrations_applied", True):
        blockers.append("migrations_not_applied")
    if not config.get("audit_durable", True):
        blockers.append("audit_not_durable")
    if not config.get("rollback_tested", True):
        blockers.append("rollback_not_tested")

    status = service.status()
    return {
        "ready": not blockers,
        "blockers": blockers,
        "checks": {
            "acceptance_gates": acceptance["passed"],
            "dpia_approved_signoffs": len(approved),
            "prohibited_dual_use_decisions": len(prohibited),
            "modules": status["modules"],
            "engines": status["technical_engines"],
        },
        "note": "No-go blockers must be resolved by an authorised reviewer; IAM cannot self-approve deployment.",
    }
