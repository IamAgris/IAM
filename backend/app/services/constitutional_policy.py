"""Protected-core enforcement derived from IAM's operating principles (OD-11).

The constitution teaches; this module enforces. Immutable operating principles
and security boundaries are recorded at bootstrap, and the protected actions
below may not run without a signed Creator authorization. Ordinary actions are
governed by their own existing gates and pass through here unchanged.
"""

from __future__ import annotations

from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.creatorapproval_service import CreatorApprovalService

PROTECTED_ACTION = "protected_core"
PROTECTED_ACTIONS = frozenset(
    {
        "identity_change",
        "constitution_change",
        "signing_key_change",
        "financial_authority_change",
        "model_release",
        "protected_deploy",
    }
)


class ConstitutionalPolicyDenied(PermissionError):
    """Raised when a protected-core action lacks signed authorization."""


async def assert_allowed(
    db: AsyncSession, action: str, *, actor: str = "iam"
) -> Dict[str, Any]:
    if action not in PROTECTED_ACTIONS:
        return {"allowed": True, "basis": "ordinary_action", "action": action}
    authority = await CreatorApprovalService(db).check_authorization(
        PROTECTED_ACTION, target_ref=action
    )
    if not authority.get("authorized"):
        raise ConstitutionalPolicyDenied(
            f"protected action {action} requires a signed Creator authorization"
        )
    return {
        "allowed": True,
        "basis": "signed_creator_authorization",
        "action": action,
        "authorization_id": str(authority.get("authorization_id")),
        "actor": actor,
    }
