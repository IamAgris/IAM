"""Encrypted website credential vault (Phase 9).

Raw passwords are encrypted at rest with the existing AES-GCM service and are
returned only once at creation/rotation/reveal. Values are never logged.
Secrets can also be referenced by environment-variable name instead of being
stored in the database.
"""

import secrets
import string
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.digital_access import WebsiteCredential
from app.models.security import AuditEvent
from app.services.creatorapproval_service import CreatorApprovalService
from app.services.crypto_service import crypto
from app.services.digitalassets_service import validate_owner_entity

REVEAL_ACTION = "credential.reveal"
ROTATE_ACTION = "credential.rotate"
_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*-_=+"


class CredentialError(PermissionError):
    """Raised when a vault operation breaks provenance or authority rules."""


def generate_password(length: int = 24) -> str:
    if length < 16:
        raise CredentialError("generated passwords must be at least 16 characters")
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


class WebsiteCredentialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _row(self, credential_id: str) -> WebsiteCredential:
        try:
            identifier = UUID(str(credential_id))
        except (ValueError, TypeError) as exc:
            raise LookupError("website credential not found") from exc
        result = await self.db.execute(
            select(WebsiteCredential).where(WebsiteCredential.id == identifier)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise LookupError("website credential not found")
        return row

    async def _authority(self, action: str, target: str) -> Dict[str, Any]:
        authority = await CreatorApprovalService(self.db).check_authorization(
            action, requested_level="3", target_ref=target
        )
        if not authority.get("authorized"):
            raise CredentialError(f"signed Creator authorization required for {action}")
        return authority

    async def register(
        self,
        *,
        site: str,
        url: str,
        username: str,
        owner_entity: str,
        password: Optional[str],
        secret_env_var: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        if not site or not url or not username:
            raise CredentialError("site, url and username are required")
        if not password and not secret_env_var:
            raise CredentialError("provide a password or a secret_env_var reference")
        owner = validate_owner_entity(owner_entity)
        row = WebsiteCredential(
            site=site,
            url=url,
            username=username,
            secret_ciphertext=crypto.encrypt(password) if password else "",
            secret_env_var=secret_env_var,
            owner_entity=owner,
            provenance={"created_by": actor, "source": "generated" if password else "env_reference"},
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(row.id, actor, "website_credential_registered", {"site": site})
        await self.db.commit()
        result = self._row_dict(row)
        if password:
            result["password"] = password  # shown once, never stored in plaintext
        return result

    async def list(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(WebsiteCredential))
        return [self._row_dict(row) for row in result.scalars().all()]

    async def reveal(self, credential_id: str, actor: str) -> Dict[str, Any]:
        row = await self._row(credential_id)
        authority = await self._authority(REVEAL_ACTION, str(row.id))
        await self._audit(
            row.id, actor, "website_credential_revealed",
            {"authorization_id": authority["authorization_id"]},
        )
        await self.db.commit()
        return {
            "id": str(row.id),
            "site": row.site,
            "username": row.username,
            "password": crypto.decrypt(row.secret_ciphertext) if row.secret_ciphertext else None,  # type: ignore[arg-type]
            "secret_env_var": row.secret_env_var,
        }

    async def rotate(self, credential_id: str, actor: str) -> Dict[str, Any]:
        row = await self._row(credential_id)
        authority = await self._authority(ROTATE_ACTION, str(row.id))
        new_password = generate_password()
        row.secret_ciphertext = crypto.encrypt(new_password)  # type: ignore[assignment]
        row.rotated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self._audit(
            row.id, actor, "website_credential_rotated",
            {"authorization_id": authority["authorization_id"]},
        )
        await self.db.commit()
        return {"id": str(row.id), "password": new_password, "rotated_at": row.rotated_at.isoformat()}

    async def revoke(self, credential_id: str, actor: str) -> Dict[str, Any]:
        row = await self._row(credential_id)
        row.is_active = False  # type: ignore[assignment]
        row.revoked_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self._audit(row.id, actor, "website_credential_revoked", {})
        await self.db.commit()
        return {"id": str(row.id), "is_active": False}

    async def _audit(self, target: Any, actor: str, event: str, details: Dict[str, Any]) -> None:
        self.db.add(
            AuditEvent(event_type=event, actor=actor, target=str(target), details=details)
        )

    @staticmethod
    def _row_dict(row: WebsiteCredential) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "site": row.site,
            "url": row.url,
            "username": row.username,
            "secret_env_var": row.secret_env_var,
            "owner_entity": row.owner_entity,
            "provenance": row.provenance or {},
            "is_active": bool(row.is_active),
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "rotated_at": row.rotated_at.isoformat() if row.rotated_at else None,
            "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
            "has_stored_secret": bool(row.secret_ciphertext),
        }
