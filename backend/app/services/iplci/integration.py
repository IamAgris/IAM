"""Production integration helpers for the IPLCI enforcement gateway.

Use these from any service that has a database session. The gateway built here
is backed by the durable ``ip_legal_*`` tables and the active signed policy, so
an enforcement decision is both binding and auditable.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.iplci import policy
from app.services.iplci.gateway import ComplianceGateway
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


async def enforce_training_request(
    db: AsyncSession,
    *,
    source_id: Optional[str],
    dataset_id: Optional[str],
    approval_id: Optional[str] = None,
    agent_id: str = "main",
    jurisdiction: Optional[str] = None,
) -> Dict[str, Any]:
    """Mandatory gate for a training request. Fails closed on missing context."""
    gateway = await gateway_for_db(db)
    return await gateway.enforce_training(
        source_id=source_id,
        dataset_id=dataset_id,
        approval_id=approval_id,
        agent_id=agent_id,
        jurisdiction=jurisdiction,
    )


async def enforce_collection_request(
    db: AsyncSession,
    *,
    source_id: Optional[str],
    agent_id: str = "main",
) -> Dict[str, Any]:
    """Mandatory gate for collecting/ingesting external material."""
    gateway = await gateway_for_db(db)
    return await gateway.enforce_collection(source_id=source_id, agent_id=agent_id)


async def enforce_agent_request(
    db: AsyncSession,
    *,
    action: str,
    source_id: Optional[str],
    agent_id: str,
    jurisdiction: Optional[str] = None,
) -> Dict[str, Any]:
    """Mandatory gate for an agent action before dispatch."""
    gateway = await gateway_for_db(db)
    return await gateway.enforce_agent_action(
        action=action, source_id=source_id, agent_id=agent_id, jurisdiction=jurisdiction
    )
