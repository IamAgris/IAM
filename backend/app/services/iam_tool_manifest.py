"""Callable tool manifests for IAM's two decision paths.

Registration in ``ToolRegistry`` makes a capability *permitted*; this module
makes the safe subset *offerable* to the local primary model and *selectable*
by the autonomy graph. Consequential and approval-bearing actions are
intentionally absent: they remain reachable only through their governed routes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autonomy import ToolPermission, ToolRegistry
from app.services.iics.tool_registry import IICS_TOOLS

CORE_TOOLS: tuple[Mapping[str, Any], ...] = (
    {
        "name": "tone.analyze",
        "description": (
            "Analyse text for defensive tone, register and influence indicators. "
            "This is analysis, not a diagnosis or an instruction to act."
        ),
        "category": "social",
        "parameters": {"text": "string"},
        "permission_level": "autonomous",
    },
    {
        "name": "network.inspect",
        "description": (
            "List registered external AI agents and their trust status without "
            "contacting them."
        ),
        "category": "network",
        "parameters": {},
        "permission_level": "autonomous",
    },
    {
        "name": "sandbox.status",
        "description": (
            "Read free-sandbox policy and environment status. Never provisions "
            "or spends anything."
        ),
        "category": "infrastructure",
        "parameters": {},
        "permission_level": "autonomous",
    },
    {
        "name": "finance.research.read",
        "description": (
            "Read research-only prediction-market and investment records. "
            "Never places an order, spends funds or moves value."
        ),
        "category": "finance",
        "parameters": {"limit": "integer"},
        "permission_level": "autonomous",
    },
)

# IICS tools with a deterministic, bounded handler in iam_tool_executor.py.
# iics.authorize, iics.qa.run and iics.creator.approval_request stay route-only.
EXECUTABLE_IICS_TOOLS: frozenset[str] = frozenset(
    {
        "iics.egress.check",
        "iics.research.strategy",
        "iics.source.register",
        "iics.schedule.create",
        "iics.creator.notify",
    }
)

def wire_name(name: str) -> str:
    """Provider-safe tool name (OpenAI-compatible: letters, digits, _, -)."""
    return name.replace(".", "_")


def resolve_wire_name(name: str) -> str:
    """Map a provider-safe name back to its registered IAM tool name."""
    for registered in executable_tool_names():
        if wire_name(registered) == name:
            return registered
    return name


_JSON_TYPES: Dict[str, str] = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "list": "array",
    "object": "object",
    "boolean": "boolean",
}


def _schema(manifest: Mapping[str, Any]) -> Dict[str, Any]:
    """Convert a registry manifest into an OpenAI-compatible function schema."""
    properties: Dict[str, Any] = {}
    for key, kind in (manifest.get("parameters") or {}).items():
        properties[str(key)] = {
            "type": _JSON_TYPES.get(str(kind), "string"),
            "description": str(key).replace("_", " "),
        }
    return {
        "type": "function",
        "function": {
            "name": wire_name(str(manifest["name"])),
            "description": str(manifest.get("description") or "")[:1000],
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": [],
            },
        },
    }


def callable_manifests() -> List[Mapping[str, Any]]:
    """All manifests with a real executor, in a stable order."""
    return [
        *CORE_TOOLS,
        *(m for m in IICS_TOOLS if str(m.get("name")) in EXECUTABLE_IICS_TOOLS),
    ]


def model_tool_schemas() -> List[Dict[str, Any]]:
    """Tool schemas to offer alongside the built-in web search."""
    return [_schema(manifest) for manifest in callable_manifests()]


def executable_tool_names() -> frozenset[str]:
    """Exact names the inference layer will execute."""
    return frozenset(str(m["name"]) for m in callable_manifests())


async def register_core_tools(db: AsyncSession) -> List[Dict[str, Any]]:
    """Idempotently register the core tool manifests and permission levels."""
    registered: List[Dict[str, Any]] = []
    for manifest in CORE_TOOLS:
        name = str(manifest["name"])
        result = await db.execute(select(ToolRegistry).where(ToolRegistry.name == name))
        tool = result.scalar_one_or_none()
        if tool is None:
            tool = ToolRegistry(
                name=name,
                description=str(manifest.get("description") or ""),
                category=str(manifest.get("category") or "iam"),
                parameters=dict(manifest.get("parameters") or {}),
                is_active=True,
            )
            db.add(tool)
            await db.flush()
            perm_result = await db.execute(
                select(ToolPermission).where(ToolPermission.tool_id == tool.id)
            )
            if perm_result.scalar_one_or_none() is None:
                db.add(
                    ToolPermission(
                        tool_id=tool.id,
                        permission_level=str(
                            manifest.get("permission_level") or "autonomous"
                        ),
                        requires_human_approval=bool(
                            manifest.get("requires_human_approval", False)
                        ),
                    )
                )
            status = "registered"
        else:
            status = "existing"
        registered.append({"name": name, "status": status})
    await db.commit()
    return registered
