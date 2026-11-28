"""Allowlisted execution adapter for IAM's durable autonomy graph.

This is not a new subsystem. It is the execution edge of the single autonomy
orchestrator: the graph selects one of these actions, and this module calls the
existing IAM service that implements it. Unknown actions fail closed, and every
outcome carries structured evidence so the verification node can check a
persisted result instead of trusting a status string.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from app.services.module_registry import available_actions

# The allowlist is derived from the central module contract registry so a new
# action must be declared once, with its authority, before it can be dispatched.
AVAILABLE: tuple[str, ...] = available_actions()

TOOL_ACTIONS: Mapping[str, str] = {
    "tone_analyze": "tone.analyze",
    "network_inspect": "network.inspect",
    "sandbox_status": "sandbox.status",
    "finance_research_read": "finance.research.read",
    "iics_egress_check": "iics.egress.check",
}


def _failure(action: str, exc: BaseException) -> Dict[str, Any]:
    """Return a safe failure without echoing credentials or raw content."""
    return {
        "status": "failure",
        "action": action,
        "error": type(exc).__name__,
        "detail": str(exc)[:300],
    }


async def dispatch(db: Any, action: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Execute one allowlisted action against a real IAM service.

    ``db`` is the caller's database session. Returned evidence is deliberately
    small (counts, identifiers, modes) and never contains private memory text.
    """
    if action not in AVAILABLE:
        return {"status": "failure", "action": action, "error": "unknown_action"}

    from app.services.iplci.context import resolve_governance_context

    governance = payload.get("governance_context") or {}
    resolved_governance = resolve_governance_context(governance)
    if resolved_governance:
        from app.services.iplci.gateway import GovernanceRefusal
        from app.services.iplci.integration import enforce_agent_request

        try:
            await enforce_agent_request(
                db,
                action=action,
                source_id=resolved_governance["source_id"],
                agent_id=str(resolved_governance.get("agent_id") or "main"),
                jurisdiction=resolved_governance.get("jurisdiction"),
            )
        except GovernanceRefusal as exc:
            return {
                "status": "failure",
                "action": action,
                "error": "IPLCI_GOVERNANCE_REFUSED",
                "detail": str(exc)[:300],
            }

    try:
        if action == "memory_recall":
            from app.services.memory_service import MemoryService

            items = await MemoryService(db).search_memory(
                query=str(payload.get("query") or ""),
                limit=int(payload.get("limit") or 5),
            )
            return {
                "status": "success",
                "action": action,
                "service": "MemoryService",
                "evidence": {
                    "count": len(items),
                    "memory_ids": [str(item.get("id")) for item in items[:5]],
                },
            }

        if action == "capability_inspect":
            from app.services.capability_service import CapabilityService

            items = await CapabilityService(db).list_capabilities()
            return {
                "status": "success",
                "action": action,
                "service": "CapabilityService",
                "evidence": {
                    "count": len(items),
                    "capability_ids": [str(item.get("id")) for item in items[:5]],
                },
            }

        if action == "governance_check":
            from app.services.governance_service import GovernanceService

            decision = await GovernanceService(db).check_authority(
                str(payload.get("permission_action") or "internal_reasoning"),
                str(payload.get("level") or "1"),
            )
            return {
                "status": "success",
                "action": action,
                "service": "GovernanceService",
                "evidence": {
                    "permitted": bool(decision.get("permitted")),
                    "decision": str(decision.get("decision") or "")[:200],
                },
            }

        if action == "model_probe":
            from app.services.model_inference import inference_service

            status = await inference_service.resolve()
            return {
                "status": "success",
                "action": action,
                "service": "InferenceService",
                "evidence": {
                    "available": bool(status.available),
                    "mode": status.mode,
                    "model": status.model,
                },
            }

        if action in TOOL_ACTIONS:
            from app.services.iam_tool_executor import execute_registered_tool

            tool_args: Dict[str, Any] = {}
            if action == "tone_analyze":
                tool_args = {"text": str(payload.get("text") or "")[:4000]}
            elif action == "iics_egress_check":
                tool_args = {"url": str(payload.get("url") or "")[:500]}
            elif action == "finance_research_read":
                tool_args = {"limit": payload.get("limit") or 5}
            else:
                tool_args = {}
            outcome = await execute_registered_tool(db, TOOL_ACTIONS[action], tool_args)
            return {
                "status": "failure" if outcome.get("error") else "success",
                "action": action,
                "service": "IAMToolExecutor",
                "tool": TOOL_ACTIONS[action],
                "evidence": outcome,
            }

        # action == "research" — the full existing search/browse/extract pipeline.
        from app.services.research_service import ResearchService

        record = await ResearchService().research_topic(  # type: ignore[no-untyped-call]
            query=str(payload.get("query") or ""),
            store_as_memory=True,
            store_as_knowledge=True,
            max_results=int(payload.get("max_results") or 5),
        )
        return {
            "status": "success",
            "action": action,
            "service": "ResearchService",
            "evidence": {
                "query": str(record.get("query") or "")[:300],
                "source_count": len(record.get("sources") or []),
                "finding_count": len(record.get("findings") or []),
            },
        }
    except Exception as exc:  # fail closed; never convert a failure into success
        return _failure(action, exc)
