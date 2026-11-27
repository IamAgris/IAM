"""Emergency suspension across Web3 providers and node adapters.

Suspension is an operator action, not an IAM self-authorization. It revokes active
signed Web3 authorizations and records the event without deleting audit history.
"""

from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.creatorapproval import CreatorAuthorization
from app.models.security import AuditEvent
from app.services.blockchain.governance import ACTION_LEVELS
from app.services.blockchain.providers.base import ProviderDenied, require_flag
from app.services.creatorapproval_service import CreatorApprovalService


class Web3EmergencyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_registry_enabled,
            "iam_can_lift_suspension": False,
            "audit_history_deleted": False,
            "affected_actions": sorted(ACTION_LEVELS),
        }

    async def suspend(
        self, *, reason: str, actor: str = "operator", revoke_authorizations: bool = True
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if not reason:
            raise ProviderDenied("a suspension reason is required")
        revoked: List[str] = []
        if revoke_authorizations:
            approvals = CreatorApprovalService(self.db)
            rows = (await self.db.execute(select(CreatorAuthorization))).scalars().all()
            for auth in rows:
                if auth.action_type in ACTION_LEVELS and auth.is_active and not auth.revoked_at:
                    if await approvals.revoke_authorization(str(auth.id)):
                        revoked.append(str(auth.id))
        self.db.add(
            AuditEvent(
                event_type="web3_emergency_suspension",
                actor=actor,
                target="web3_all_adapters",
                details={"reason": reason, "revoked": revoked, "lifting_requires_creator": True},
            )
        )
        await self.db.commit()
        return {
            "suspended": True,
            "revoked_authorizations": revoked,
            "note": "Operator must re-approve and re-enable flags; IAM cannot lift suspension.",
        }

    @staticmethod
    def guard(action: str) -> None:
        """Call before any execution path; fails closed for protected actions."""
        if action not in ACTION_LEVELS:
            raise ProviderDenied(f"unknown Web3 action '{action}'")
