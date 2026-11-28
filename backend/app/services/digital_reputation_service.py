"""Digital Reputation & Trust service.

Tracks per-website account reputation: verification status, platform warnings,
suspensions, ToS/privacy policy change detection, security scores,
identity consistency, and ownership evidence.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.web_knowledge import DigitalReputation, WebsiteKnowledge


class DigitalReputationError(PermissionError):
    """Raised when a reputation operation fails."""


class DigitalReputationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _reputation(self, reputation_id: str) -> DigitalReputation:
        try:
            identifier = UUID(str(reputation_id))
        except (ValueError, TypeError) as exc:
            raise ValueError("Invalid reputation ID") from exc
        result = await self.db.execute(
            select(DigitalReputation).where(DigitalReputation.id == identifier)
        )
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError("Digital reputation record not found")
        return row

    async def create(
        self,
        *,
        website_knowledge_id: str,
        account_username: str,
        verification_status: str = "unverified",
        platform_warnings: Optional[List[Dict[str, Any]]] = None,
        suspensions: Optional[List[Dict[str, Any]]] = None,
        restrictions: Optional[List[Dict[str, Any]]] = None,
        tos_changes: Optional[List[Dict[str, Any]]] = None,
        privacy_changes: Optional[List[Dict[str, Any]]] = None,
        service_reliability_score: int = 50,
        account_security_score: int = 50,
        identity_consistency_score: int = 50,
        ownership_evidence: Optional[List[Dict[str, Any]]] = None,
        actor: str,
    ) -> Dict[str, Any]:
        """Create a digital reputation record for a website account."""
        valid_statuses = ("unverified", "verified", "disputed")
        if verification_status not in valid_statuses:
            raise DigitalReputationError(
                f"Invalid verification status: {verification_status}"
            )
        valid_scores = (
            service_reliability_score,
            account_security_score,
            identity_consistency_score,
        )
        if not all(0 <= s <= 100 for s in valid_scores):
            raise DigitalReputationError("Scores must be between 0 and 100")

        row = DigitalReputation(
            website_knowledge_id=UUID(str(website_knowledge_id)),
            account_username=account_username,
            verification_status=verification_status,
            platform_warnings=platform_warnings or [],
            suspensions=suspensions or [],
            restrictions=restrictions or [],
            tos_changes=tos_changes or [],
            privacy_changes=privacy_changes or [],
            service_reliability_score=service_reliability_score,
            account_security_score=account_security_score,
            identity_consistency_score=identity_consistency_score,
            ownership_evidence=ownership_evidence or [],
        )
        self.db.add(row)
        await self.db.flush()
        await self.db.commit()
        return self._row_dict(row)

    async def get(self, reputation_id: str) -> Dict[str, Any]:
        row = await self._reputation(reputation_id)
        return self._row_dict(row)

    async def list(self, website_knowledge_id: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(DigitalReputation))
        rows = result.scalars().all()
        if website_knowledge_id:
            rows = [r for r in rows if str(r.website_knowledge_id) == website_knowledge_id]
        return [self._row_dict(r) for r in rows]

    async def update_platform_warning(
        self,
        reputation_id: str,
        warning: Dict[str, Any],
        actor: str,
    ) -> Dict[str, Any]:
        """Add a platform warning to the reputation record."""
        row = await self._reputation(reputation_id)
        warnings = list(row.platform_warnings or [])
        warnings.append(warning)
        row.platform_warnings = warnings  # type: ignore[assignment]
        await self.db.commit()
        return self._row_dict(row)

    async def record_suspension(
        self,
        reputation_id: str,
        suspension: Dict[str, Any],
        actor: str,
    ) -> Dict[str, Any]:
        """Record a suspension event for the account."""
        row = await self._reputation(reputation_id)
        suspensions = list(row.suspensions or [])
        suspensions.append(suspension)
        row.suspensions = suspensions  # type: ignore[assignment]
        row.account_status = "suspended"  # mirror to account lifecycle if present
        await self.db.commit()
        return self._row_dict(row)

    async def record_tos_change(
        self,
        reputation_id: str,
        change: Dict[str, Any],
        actor: str,
    ) -> Dict[str, Any]:
        """Record a Terms of Service change affecting the account."""
        row = await self._reputation(reputation_id)
        changes = list(row.tos_changes or [])
        changes.append(change)
        row.tos_changes = changes  # type: ignore[assignment]
        await self.db.commit()
        return self._row_dict(row)

    async def record_privacy_change(
        self,
        reputation_id: str,
        change: Dict[str, Any],
        actor: str,
    ) -> Dict[str, Any]:
        """Record a privacy policy change affecting the account."""
        row = await self._reputation(reputation_id)
        changes = list(row.privacy_changes or [])
        changes.append(change)
        row.privacy_changes = changes  # type: ignore[assignment]
        await self.db.commit()
        return self._row_dict(row)

    @staticmethod
    def _row_dict(row: DigitalReputation) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "website_knowledge_id": str(row.website_knowledge_id),
            "account_username": row.account_username,
            "verification_status": row.verification_status,
            "platform_warnings": row.platform_warnings,
            "suspensions": row.suspensions,
            "restrictions": row.restrictions,
            "tos_changes": row.tos_changes,
            "privacy_changes": row.privacy_changes,
            "service_reliability_score": row.service_reliability_score,
            "account_security_score": row.account_security_score,
            "identity_consistency_score": row.identity_consistency_score,
            "ownership_evidence": row.ownership_evidence,
            "last_assessed_at": (
                row.last_assessed_at.isoformat() if row.last_assessed_at else None
            ),
        }