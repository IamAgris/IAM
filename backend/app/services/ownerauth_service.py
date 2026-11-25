"""Owner authorization service — human-controlled authority grants."""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.ownerauth import OwnerAuthorization


class OwnerAuthService:
    """Manages owner-granted authority. Only the owner writes these records."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def grant_authorization(
        self, action_type, max_authority_level="4", spending_limit_usd=None,
        can_create_accounts=False, can_publish_externally=False,
        can_modify_own_security=False, scope=None, granted_by="owner", expires_at=None,
    ):
        auth = OwnerAuthorization(
            action_type=action_type, max_authority_level=max_authority_level,
            spending_limit_usd=spending_limit_usd, can_create_accounts=can_create_accounts,
            can_publish_externally=can_publish_externally,
            can_modify_own_security=can_modify_own_security,
            scope=scope or {}, granted_by=granted_by, is_active=True,
        )
        if expires_at:
            auth.expires_at = datetime.fromisoformat(expires_at)
        self.db.add(auth)
        await self.db.commit()
        await self.db.refresh(auth)
        return self._to_dict(auth)

    async def check_authorization(self, action_type, requested_level="1"):
        result = await self.db.execute(
            select(OwnerAuthorization).where(
                OwnerAuthorization.action_type == action_type,
                OwnerAuthorization.is_active == True,
            )
        )
        auths = result.scalars().all()
        now = datetime.now(timezone.utc)
        levels = {"1": 1, "2": 2, "3": 3, "4": 4}
        for auth in auths:
            if auth.expires_at and auth.expires_at.replace(tzinfo=timezone.utc) < now:
                continue
            if levels.get(requested_level, 0) <= levels.get(auth.max_authority_level, 0):
                return {"authorized": True, "authorization_id": str(auth.id),
                        "max_level": auth.max_authority_level, "granted_by": auth.granted_by,
                        "scope": auth.scope}
        return {"authorized": False, "reason": "No active owner authorization", "action_type": action_type}

    async def revoke_authorization(self, authorization_id):
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

    async def list_authorizations(self):
        result = await self.db.execute(select(OwnerAuthorization))
        return [self._to_dict(a) for a in result.scalars().all()]

    def _to_dict(self, auth):
        return {
            "id": str(auth.id), "action_type": auth.action_type,
            "max_authority_level": auth.max_authority_level,
            "spending_limit_usd": float(auth.spending_limit_usd) if auth.spending_limit_usd else None,
            "can_create_accounts": auth.can_create_accounts,
            "can_publish_externally": auth.can_publish_externally,
            "can_modify_own_security": auth.can_modify_own_security,
            "is_active": auth.is_active, "granted_by": auth.granted_by,
        }
