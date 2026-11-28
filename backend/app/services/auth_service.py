"""API credential management — hashes only, plaintext returned once."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_policy import SCOPE_RANK
from app.models.auth import ApiCredential


class AuthError(PermissionError):
    """Raised for invalid credentials or unauthorized management actions."""


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def generate_key() -> str:
    return "iam_" + secrets.token_urlsafe(32)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_credential(
        self, name: str, scope: str, created_by: str
    ) -> Tuple[ApiCredential, str]:
        if scope not in SCOPE_RANK:
            raise AuthError(f"unknown scope: {scope}")
        plaintext = generate_key()
        credential = ApiCredential(
            name=name,
            key_hash=hash_key(plaintext),
            scope=scope,
            is_active=True,
            created_by=created_by,
        )
        self.db.add(credential)
        await self.db.commit()
        await self.db.refresh(credential)
        return credential, plaintext  # the only time the plaintext is available

    async def verify_key(self, key: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(ApiCredential).where(
                ApiCredential.key_hash == hash_key(key),
                ApiCredential.is_active == True,  # noqa: E712
            )
        )
        credential = result.scalar_one_or_none()
        if not credential:
            return None
        credential.last_used_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.db.commit()
        return {
            "id": str(credential.id),
            "name": credential.name,
            "scope": credential.scope,
        }

    @staticmethod
    def to_dict(credential: ApiCredential) -> Dict[str, Any]:
        return {
            "id": str(credential.id),
            "name": credential.name,
            "scope": credential.scope,
            "is_active": credential.is_active,
            "created_by": credential.created_by,
            "created_at": credential.created_at.isoformat() if credential.created_at else None,
            "last_used_at": (
                credential.last_used_at.isoformat() if credential.last_used_at else None
            ),
            "revoked_at": (
                credential.revoked_at.isoformat() if credential.revoked_at else None
            ),
        }

    async def list_credentials(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(ApiCredential).order_by(ApiCredential.created_at.desc()))
        return [self.to_dict(c) for c in result.scalars().all()]

    async def revoke_credential(self, name: str) -> bool:
        result = await self.db.execute(
            select(ApiCredential).where(ApiCredential.name == name)
        )
        credential = result.scalar_one_or_none()
        if not credential:
            return False
        credential.is_active = False  # type: ignore[assignment]
        credential.revoked_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.db.commit()
        return True
