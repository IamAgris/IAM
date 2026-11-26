"""Enforcement of ToolPermission at tool-call time.

The tool registry in routes/tools.py stores permission levels but previously
nothing consulted them before an autonomous step ran. This module is the single
deterministic gate: unknown, inactive, blocked and approval-required tools are
refused before any action is taken.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.autonomy import ToolPermission, ToolRegistry


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
) -> str:
    """Return the granted permission level or raise ToolAuthorizationError.

    ``approval_granted`` must come from a signed Creator/authority decision;
    it is never inferred from the model's own plan.
    """
    if not tool_name:
        raise ToolAuthorizationError("tool_name_required", "tool_name_required")

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
    if level == "explicit" and not approval_granted:
        raise ToolAuthorizationError("explicit_approval_required", "approval_required")
    if permission.requires_human_approval and not approval_granted:
        raise ToolAuthorizationError("human_approval_required", "approval_required")
    if level not in ("autonomous", "authorized", "explicit"):
        raise ToolAuthorizationError("unknown_permission_level", "tool_blocked")

    return level
