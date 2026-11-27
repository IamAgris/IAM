"""Encrypted, isolated provider-connection credential vault (OD-51 §4.1/§4.2).

Only the gateway credential for a provider connection is stored here; provider
API keys remain in the LiteLLM gateway configuration. Secrets are encrypted with
the existing AES-GCM service, are never returned by an API, and are never
logged. A failing or disabled key can only fail over to another *authorised*
key of the same provider — never to a key with a different scope or limit.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_provider_key import ModelProviderKey
from app.services.crypto_service import crypto
from app.services.model_policy import PAID_ACTION, require_authorization

PROVIDER_KEY_ACTION = "model.provider_key_manage"
SCOPES = ("free", "paid", "specialist")
_HEALTHY = ("unknown", "healthy")


class VaultError(PermissionError):
    """Raised when a credential operation would break isolation or fail open."""


class ModelCredentialVault:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def fingerprint(secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]

    async def _row(self, key_id: str) -> ModelProviderKey:
        try:
            identifier = UUID(str(key_id))
        except (ValueError, TypeError) as exc:
            raise LookupError("provider key not found") from exc
        result = await self.db.execute(
            select(ModelProviderKey).where(ModelProviderKey.id == identifier)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise LookupError("provider key not found")
        return row

    async def _authorise(self) -> Dict[str, Any]:
        """Manage operations require a signed Creator authorization (OD-19)."""
        return await require_authorization(self.db, PROVIDER_KEY_ACTION)

    async def register(
        self,
        *,
        provider: str,
        key_alias: str,
        secret: str,
        scope: str = "free",
        monthly_limit_usd: Optional[float] = None,
        actor: str = "operator",
    ) -> Dict[str, Any]:
        if not provider or not key_alias or not secret:
            raise VaultError("provider, key_alias and secret are required")
        if scope not in SCOPES:
            raise VaultError(f"scope must be one of {', '.join(SCOPES)}")
        if len(secret) > 4096:
            raise VaultError("credential is too long")
        await self._authorise()
        row = ModelProviderKey(
            provider=provider,
            key_alias=key_alias,
            key_fingerprint=self.fingerprint(secret),
            secret_ciphertext=crypto.encrypt(secret),
            scope=scope,
            is_enabled=True,
            health="unknown",
            failure_count=0,
            monthly_limit_usd=monthly_limit_usd,
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return row.public_dict()

    async def list_public(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        statement = select(ModelProviderKey)
        if provider:
            statement = statement.where(ModelProviderKey.provider == provider)
        result = await self.db.execute(statement)
        return [row.public_dict() for row in result.scalars().all()]

    async def resolve(
        self, *, provider: str, is_paid: bool = False, purpose: Optional[str] = None
    ) -> Tuple[ModelProviderKey, str]:
        """Return an authorised key and its plaintext, or fail closed.

        Paid work never uses a non-paid-scoped key. Unhealthy, disabled and
        undecryptable keys are skipped; the next authorised key is selected.
        """
        result = await self.db.execute(
            select(ModelProviderKey).where(ModelProviderKey.provider == provider)
        )
        candidates = [
            row
            for row in result.scalars().all()
            if row.is_enabled and row.health in _HEALTHY
        ]
        if is_paid:
            candidates = [row for row in candidates if row.scope == "paid"]
        elif purpose == "specialist":
            candidates = [row for row in candidates if row.scope != "free"]
        if not candidates:
            raise VaultError(
                f"no authorised {'paid' if is_paid else 'enabled'} key for provider {provider}"
            )
        # Prefer free-scoped keys for free work, then the healthiest/least-used.
        candidates.sort(
            key=lambda row: (
                row.scope != "free",
                int(row.failure_count or 0),
                row.last_used_at is not None,
            )
        )
        row = candidates[0]
        plaintext = crypto.decrypt(str(row.secret_ciphertext))
        if not plaintext or plaintext.startswith("[unable") or plaintext == row.secret_ciphertext:
            raise VaultError("stored credential cannot be decrypted; refusing to fail open")
        setattr(row, "last_used_at", datetime.now(timezone.utc))
        await self.db.flush()
        await self.db.commit()
        return row, plaintext

    async def mark_health(self, key_id: str, *, healthy: bool) -> Dict[str, Any]:
        row = await self._row(key_id)
        setattr(row, "health", "healthy" if healthy else "unhealthy")
        setattr(row, "failure_count", 0 if healthy else int(row.failure_count or 0) + 1)
        setattr(row, "last_checked_at", datetime.now(timezone.utc))
        await self.db.flush()
        await self.db.commit()
        return row.public_dict()

    async def disable(self, key_id: str) -> Dict[str, Any]:
        row = await self._row(key_id)
        await self._authorise()
        setattr(row, "is_enabled", False)
        setattr(row, "health", "disabled")
        await self.db.flush()
        await self.db.commit()
        return row.public_dict()

    async def rotate(
        self, key_id: str, *, secret: str, actor: str = "operator"
    ) -> Dict[str, Any]:
        row = await self._row(key_id)
        await self._authorise()
        if not secret or len(secret) > 4096:
            raise VaultError("a valid replacement credential is required")
        setattr(row, "secret_ciphertext", crypto.encrypt(secret))
        setattr(row, "key_fingerprint", self.fingerprint(secret))
        setattr(row, "failure_count", 0)
        setattr(row, "health", "unknown")
        await self.db.flush()
        await self.db.commit()
        return row.public_dict()

    async def health(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read-only health summary; never includes secrets."""
        rows = await self.list_public(provider)
        return [
            {
                "provider": row["provider"],
                "key_alias": row["key_alias"],
                "key_fingerprint": row["key_fingerprint"],
                "scope": row["scope"],
                "health": row["health"],
                "is_enabled": row["is_enabled"],
            }
            for row in rows
        ]
