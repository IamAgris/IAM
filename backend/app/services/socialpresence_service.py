"""Verified external social presence (OD-30), owned by a legal entity."""

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import AuditEvent
from app.models.socialintel import SocialPresence
from app.services.creatorapproval_service import CreatorApprovalService
from app.services.digitalassets_service import validate_owner_entity

REGISTER_ACTION = "social.presence_register"
VERIFY_ACTION = "social.presence_verify"


class SocialPresenceError(PermissionError):
    """Raised when a presence record lacks provenance or signed authority."""


class SocialPresenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _presence(self, presence_id: str) -> SocialPresence:
        try:
            identifier = UUID(str(presence_id))
        except (ValueError, TypeError) as exc:
            raise LookupError("social presence not found") from exc
        result = await self.db.execute(
            select(SocialPresence).where(SocialPresence.id == identifier)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise LookupError("social presence not found")
        return row

    async def register(
        self,
        *,
        platform: str,
        handle: str,
        profile_url: str,
        owner_entity: str,
        approval_id: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        if not platform or not handle:
            raise SocialPresenceError("platform and handle are required")
        parsed = urlparse(profile_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise SocialPresenceError("profile_url must be an http(s) URL")
        owner = validate_owner_entity(owner_entity)
        if not approval_id:
            raise SocialPresenceError("presence registration requires signed Creator authority")
        authority = await CreatorApprovalService(self.db).check_authorization(
            REGISTER_ACTION, requested_level="3", target_ref=profile_url
        )
        if not authority.get("authorized"):
            raise SocialPresenceError("no active signed Creator authorization for this URL")
        row = SocialPresence(
            platform=platform.strip(),
            handle=handle.strip(),
            profile_url=profile_url.strip(),
            owner_entity=owner,
            verified=False,
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(
            row.id, actor, "social_presence_registered",
            {"platform": platform, "owner_entity": owner, "verified": False},
        )
        await self.db.commit()
        return self._row(row)

    async def verify(
        self, presence_id: str, approval_id: str, actor: str
    ) -> Dict[str, Any]:
        row = await self._presence(presence_id)
        authority = await CreatorApprovalService(self.db).check_authorization(
            VERIFY_ACTION, requested_level="3", target_ref=str(row.id)
        )
        if not authority.get("authorized"):
            raise SocialPresenceError("no signed Creator authorization for this verification")
        if approval_id and authority.get("authorization_id") != approval_id:
            raise SocialPresenceError("approval_id does not match the active authorization")
        row.verified = True  # type: ignore[assignment]
        row.verification_ref = str(authority["authorization_id"])  # type: ignore[assignment]
        await self._audit(
            row.id, actor, "social_presence_verified",
            {"verification_ref": row.verification_ref},
        )
        await self.db.commit()
        return self._row(row)

    async def list(self, verified_only: bool = False) -> List[Dict[str, Any]]:
        query = select(SocialPresence)
        if verified_only:
            query = query.where(SocialPresence.verified.is_(True))
        result = await self.db.execute(query.order_by(SocialPresence.created_at.desc()))
        return [self._row(row) for row in result.scalars().all()]

    async def _audit(self, target: Any, actor: str, event: str, details: Dict[str, Any]) -> None:
        self.db.add(AuditEvent(event_type=event, actor=actor, target=str(target), details=details))

    @staticmethod
    def _row(row: SocialPresence) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "platform": row.platform,
            "handle": row.handle,
            "profile_url": row.profile_url,
            "owner_entity": row.owner_entity,
            "verified": bool(row.verified),
            "verification_ref": row.verification_ref,
            "is_active": bool(row.is_active),
        }
