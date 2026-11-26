"""Legacy owner authorization records — historical only, never an authority source.

OD-03/OD-04 locked a single authority path: per-action signed Creator requests.
The old ``owner_authorizations`` table remains only so existing rows can be
inspected and revoked. It cannot grant authority and no new rows can be created.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ownerauth import OwnerAuthorization


class LegacyAuthorityError(PermissionError):
    """Raised when someone tries to create a standing owner grant."""


class OwnerAuthService:
    """Read/revoke-only view of legacy grants (OD-03/OD-04 reconciliation)."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def grant_authorization(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        raise LegacyAuthorityError(
            "legacy standing owner grants are disabled; use the signed Creator "
            "approval flow at /api/v1/creator/requests"
        )

    async def check_authorization(
        self, action_type: str, requested_level: str = "1"
    ) -> Dict[str, Any]:
        """Always fail closed — legacy rows are not authority."""
        result = await self.db.execute(
            select(OwnerAuthorization).where(
                OwnerAuthorization.action_type == action_type,
                OwnerAuthorization.is_active.is_(True),
            )
        )
        legacy_rows = result.scalars().all()
        return {
            "authorized": False,
            "reason": (
                "Legacy owner grants are not an authority source (OD-03/OD-04); "
                "a signed Creator authorization is required"
            ),
            "action_type": action_type,
            "legacy_grants_found": len(legacy_rows),
            "authority_source": "creator_signed_request_only",
        }

    async def revoke_authorization(self, authorization_id: Any) -> bool:
        result = await self.db.execute(
            select(OwnerAuthorization).where(OwnerAuthorization.id == authorization_id)
        )
        auth = result.scalar_one_or_none()
        if not auth:
            return False
        auth.is_active = False
        auth.revoked_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True

    async def list_authorizations(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(OwnerAuthorization))
        return [
            {
                **self._to_dict(auth),
                "authority_source": False,
                "note": "historical record only; cannot grant authority",
            }
            for auth in result.scalars().all()
        ]

    @staticmethod
    def _to_dict(auth: OwnerAuthorization) -> Dict[str, Any]:
        return {
            "id": str(auth.id),
            "action_type": auth.action_type,
            "max_authority_level": auth.max_authority_level,
            "spending_limit_usd": (
                float(auth.spending_limit_usd) if auth.spending_limit_usd else None
            ),
            "can_create_accounts": auth.can_create_accounts,
            "can_publish_externally": auth.can_publish_externally,
            "can_modify_own_security": auth.can_modify_own_security,
            "is_active": auth.is_active,
            "granted_by": auth.granted_by,
        }
