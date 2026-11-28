"""Register IICS capabilities as tools the local primary model can invoke.

Qwen decides *which* tool to call; IAM executes it deterministically through
the existing ToolRegistry/ToolPermission gate (tool_authorization.py).
Free public tools are autonomous; consequential Creator actions are explicit.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autonomy import ToolPermission, ToolRegistry

IICS_TOOLS: List[Mapping[str, Any]] = [
    {
        "name": "iics.egress.check",
        "description": "Assess a URL against the egress/SSRF policy without fetching it.",
        "category": "internet",
        "parameters": {"url": "string"},
        "permission_level": "autonomous",
    },
    {
        "name": "iics.authorize",
        "description": "Combine internet permissions with the mandatory legal gateway.",
        "category": "internet",
        "parameters": {"action_type": "string", "url": "string", "purpose": "string"},
        "permission_level": "autonomous",
    },
    {
        "name": "iics.research.strategy",
        "description": "Choose a documented research strategy and generate queries.",
        "category": "research",
        "parameters": {"question": "string", "known_domains": "list", "prior_confidence": "number"},
        "permission_level": "autonomous",
    },
    {
        "name": "iics.source.register",
        "description": "Register a source with rights, TTL class and legal provenance.",
        "category": "research",
        "parameters": {"url": "string", "licence": "string", "rights": "object"},
        "permission_level": "autonomous",
    },
    {
        "name": "iics.schedule.create",
        "description": "Create a governed recurring research job on the ARQ runtime.",
        "category": "research",
        "parameters": {"goal": "string", "query": "string", "cadence_minutes": "integer"},
        "permission_level": "autonomous",
    },
    {
        "name": "iics.qa.run",
        "description": "Run scored internet QA benchmarks and persist the results.",
        "category": "governance",
        "parameters": {},
        "permission_level": "autonomous",
    },
    {
        "name": "iics.creator.notify",
        "description": "Send an informational Creator email (never authority-bearing).",
        "category": "governance",
        "parameters": {"update": "string", "context": "string"},
        "permission_level": "autonomous",
    },
    {
        "name": "iics.creator.approval_request",
        "description": "Raise a signed Creator challenge for a consequential action.",
        "category": "governance",
        "parameters": {"action_type": "string", "summary": "string", "target_ref": "string"},
        "permission_level": "explicit",
        "requires_human_approval": True,
    },
]


class ToolRegistryError(PermissionError):
    """Raised when a tool manifest is invalid."""


async def register_iics_tools(db: AsyncSession) -> List[Dict[str, Any]]:
    """Idempotently register tools and their permission levels."""
    registered: List[Dict[str, Any]] = []
    for manifest in IICS_TOOLS:
        name = str(manifest["name"])
        result = await db.execute(select(ToolRegistry).where(ToolRegistry.name == name))
        tool = result.scalar_one_or_none()
        if not tool:
            tool = ToolRegistry(
                name=name,
                description=str(manifest.get("description") or ""),
                category=str(manifest.get("category") or "iics"),
                parameters=dict(manifest.get("parameters") or {}),
                is_active=True,
            )
            db.add(tool)
            await db.flush()
            db.add(
                ToolPermission(
                    tool_id=tool.id,
                    permission_level=str(manifest.get("permission_level") or "autonomous"),
                    requires_human_approval=bool(manifest.get("requires_human_approval", False)),
                )
            )
            registered.append({"name": name, "status": "registered"})
        else:
            registered.append({"name": name, "status": "existing"})
    await db.commit()
    return registered
