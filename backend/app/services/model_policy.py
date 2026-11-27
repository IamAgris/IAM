"""Signed-authorization enforcement for paid inference and chat actions.

The router's ``allow_paid`` boolean used to be self-declared by the caller.
OD-04/OD-46 require explicit owner authorization for paid use, and the chat
routes are public. These helpers make the signed Creator authorization the
authority rather than a caller-supplied flag.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.creatorapproval_service import CreatorApprovalService

PAID_ACTION = "model.paid_inference"
SKILL_ACTION = "model.skill_invocation"


class ModelPolicyDenied(PermissionError):
    """Raised when an action lacks an active signed Creator authorization."""

    def __init__(self, action: str, target: Optional[str] = None):
        self.action = action
        self.target = target
        super().__init__(
            f"no active signed Creator authorization for {action}"
            + (f" on {target}" if target else "")
        )


async def require_authorization(
    db: AsyncSession,
    action: str,
    *,
    target_ref: Optional[str] = None,
) -> Dict[str, Any]:
    authority = await CreatorApprovalService(db).check_authorization(
        action, target_ref=target_ref
    )
    if not authority.get("authorized"):
        raise ModelPolicyDenied(action, target_ref)
    return authority
