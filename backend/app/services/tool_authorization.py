"""Enforcement of ToolPermission at tool-call time.

The tool registry in routes/tools.py stores permission levels but previously
nothing consulted them before an autonomous step ran. This module is the single
deterministic gate: unknown, inactive, blocked and approval-required tools are
refused before any action is taken.
"""

from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autonomy import ToolPermission, ToolRegistry

TOOL_ACTION = "tool.invoke"


class ToolAuthorizationError(Exception):
    """Raised when a tool call is not permitted."""

    def __init__(self, reason: str, code: str):
        super().__init__(reason)
        self.reason = reason
        self.code = code


async def authorize_tool_call(
    db: AsyncSession,
    tool_name: str,
    *,
    approval_granted: bool = False,
    signed_authorization: Optional[Dict[str, Any]] = None,
    governance_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Return the granted permission level or raise ToolAuthorizationError.

    A bare ``approval_granted`` boolean is never sufficient. Explicit or
    human-approval tools require a signed Creator authorization record, either
    supplied by the caller or verified against CreatorApprovalService.
    """
    if not tool_name:
        raise ToolAuthorizationError("tool_name_required", "tool_name_required")

    from app.services.iplci.context import resolve_governance_context
    from app.services.iplci.gateway import GovernanceRefusal
    from app.services.iplci.integration import enforce_agent_request

    resolved = resolve_governance_context(governance_context)
    if resolved:
        try:
            await enforce_agent_request(
                db,
                action=TOOL_ACTION,
                source_id=resolved["source_id"],
                agent_id=str(resolved.get("agent_id") or "main"),
                jurisdiction=resolved.get("jurisdiction"),
            )
        except GovernanceRefusal as exc:
            raise ToolAuthorizationError(str(exc), exc.code)

    result = await db.execute(
        select(ToolRegistry).where(
            ToolRegistry.name == tool_name,
            ToolRegistry.is_active.is_(True),
        )
    )
    tool = result.scalar_one_or_none()
    if tool is None:
        raise ToolAuthorizationError("unknown_or_inactive_tool", "unknown_tool")

    perm_result = await db.execute(
        select(ToolPermission).where(ToolPermission.tool_id == tool.id)
    )
    permission = perm_result.scalar_one_or_none()
    if permission is None:
        raise ToolAuthorizationError("tool_permission_missing", "tool_blocked")

    level = permission.permission_level
    if level == "blocked":
        raise ToolAuthorizationError("tool_is_blocked", "tool_blocked")
    if level == "explicit" or permission.requires_human_approval:
        authority = signed_authorization
        if authority is None and approval_granted:
            from app.services.creatorapproval_service import CreatorApprovalService

            authority = await CreatorApprovalService(db).check_authorization(
                TOOL_ACTION, target_ref=tool_name
            )
        if not authority or not authority.get("authorized"):
            raise ToolAuthorizationError(
                "signed_authorization_required", "approval_required"
            )
    if level not in ("autonomous", "authorized", "explicit"):
        raise ToolAuthorizationError("unknown_permission_level", "tool_blocked")

    return str(level)
