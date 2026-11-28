"""Production integration helpers for the IPLCI enforcement gateway.

Use these from any service that has a database session. The gateway built here
is backed by the durable ``ip_legal_*`` tables and the active signed policy, so
an enforcement decision is both binding and auditable. Callers may omit the
governance context entirely when it was established at the request/agent
boundary — it is inherited automatically.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.iplci import policy
from app.services.iplci.context import resolve_governance_context
from app.services.iplci.gateway import ComplianceGateway, GovernanceRefusal
from app.services.iplci.service import IPLCIService
from app.services.iplci.store import SQLStore


async def gateway_for_db(db: AsyncSession) -> ComplianceGateway:
    """Build a DB-backed gateway with the active signed policy installed."""
    service = IPLCIService(SQLStore(db))
    gateway = ComplianceGateway(service)
    record = await service.store.active_policy()
    if record and policy.verify_policy(record):
        gateway.set_policy(record)
    return gateway


def _context(
    source_id: Optional[str],
    agent_id: str,
    jurisdiction: Optional[str] = None,
    approval_id: Optional[str] = None,
) -> Dict[str, Any]:
    context = resolve_governance_context({
        "source_id": source_id,
        "agent_id": agent_id,
        "jurisdiction": jurisdiction,
        "approval_id": approval_id,
    })
    if not context or not context.get("source_id"):
        raise GovernanceRefusal(
            "IPLCI_PROVENANCE_REQUIRED", "BLOCKED", "CRITICAL",
            "no governance context: source provenance is required",
        )
    return context


async def enforce_training_request(
    db: AsyncSession,
    *,
    source_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    approval_id: Optional[str] = None,
    agent_id: str = "main",
    jurisdiction: Optional[str] = None,
) -> Dict[str, Any]:
    """Mandatory gate for a training request. Fails closed on missing context."""
    context = _context(source_id, agent_id, jurisdiction, approval_id)
    gateway = await gateway_for_db(db)
    return await gateway.enforce_training(
        source_id=context["source_id"],
        dataset_id=dataset_id or context.get("dataset_id"),
        approval_id=context.get("approval_id"),
        agent_id=str(context.get("agent_id") or agent_id),
        jurisdiction=context.get("jurisdiction"),
    )


async def enforce_collection_request(
    db: AsyncSession,
    *,
    source_id: Optional[str] = None,
    agent_id: str = "main",
) -> Dict[str, Any]:
    """Mandatory gate for collecting/ingesting external material."""
    context = _context(source_id, agent_id)
    gateway = await gateway_for_db(db)
    return await gateway.enforce_collection(
        source_id=context["source_id"], agent_id=str(context.get("agent_id") or agent_id)
    )


async def enforce_agent_request(
    db: AsyncSession,
    *,
    action: str,
    source_id: Optional[str] = None,
    agent_id: str = "main",
    jurisdiction: Optional[str] = None,
) -> Dict[str, Any]:
    """Mandatory gate for an agent action before dispatch."""
    context = _context(source_id, agent_id, jurisdiction)
    gateway = await gateway_for_db(db)
    return await gateway.enforce_agent_action(
        action=action,
        source_id=context["source_id"],
        agent_id=str(context.get("agent_id") or agent_id),
        jurisdiction=context.get("jurisdiction"),
    )
