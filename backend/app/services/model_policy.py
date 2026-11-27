"""Signed-authorization enforcement for paid inference and chat actions.

The router's ``allow_paid`` boolean used to be self-declared by the caller.
OD-04/OD-46 require explicit owner authorization for paid use, and the chat
routes are public. These helpers make the signed Creator authorization the
authority rather than a caller-supplied flag.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.modelrouter import DiscoveredModel
from app.services.creatorapproval_service import CreatorApprovalService

PAID_ACTION = "model.paid_inference"
SKILL_ACTION = "model.skill_invocation"
SEARCH_ACTION = "search.paid_provider"
KNOWN_PAID_ALIASES = frozenset({"gpt-4o-mini", "claude-3-haiku"})


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
    if settings.free_models_only and action in {PAID_ACTION, SEARCH_ACTION}:
        raise ModelPolicyDenied(action, target_ref)
    authority = await CreatorApprovalService(db).check_authorization(
        action, target_ref=target_ref
    )
    if not authority.get("authorized"):
        raise ModelPolicyDenied(action, target_ref)
    return authority


async def is_paid_model(db: AsyncSession, model: Optional[str]) -> bool:
    """Determine whether an alias is a paid provider, not merely hosted."""
    if not model:
        return False
    from app.services.model_inference import InferenceService

    if InferenceService._is_local_alias(model):
        return False
    if model in KNOWN_PAID_ALIASES:
        return True
    try:
        result = await db.execute(
            select(DiscoveredModel).where(DiscoveredModel.model_id == model)
        )
        entry = cast(Any, result.scalar_one_or_none())
        return bool(entry is not None and not bool(entry.is_free))
    except Exception:  # pragma: no cover - catalog may be unavailable
        return False


async def require_paid_authorization(db: AsyncSession, model: Optional[str]) -> Any:
    """Require a signed authorization when the selected model is a paid alias."""
    if await is_paid_model(db, model):
        return await require_authorization(db, PAID_ACTION, target_ref=model)
    return None
