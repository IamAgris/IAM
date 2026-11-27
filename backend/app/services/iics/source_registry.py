"""Source rights, freshness TTL, claim evidence and revocation propagation.

IICS gap closures §2.2 (TTL/claim labels) and §2.7 (source registry).
Confidence thresholds follow the pending addendum: <0.40 unverified,
0.40-0.69 provisional, >=0.70 verified.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.iics import IICSClaim, IICSSource

FRESHNESS_TTL_HOURS: Dict[str, int] = {
    "volatile": 24,
    "documentation": 24 * 30,
    "standard": 24 * 180,
    "stable": 24 * 365,
}


def label_for_confidence(confidence: float) -> str:
    if confidence < 0.40:
        return "unverified"
    if confidence < 0.70:
        return "provisional"
    return "verified"


class SourceRegistry:
    """Governed per-source record with rights, TTL and claim provenance."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _row_dict(row: IICSSource) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "url": row.url,
            "domain": row.domain,
            "source_type": row.source_type,
            "licence": row.licence,
            "rights": dict(row.rights or {}),
            "territory": row.territory,
            "freshness_class": row.freshness_class,
            "reliability_score": float(row.reliability_score or 0),
            "conditions": list(row.conditions or []),
            "legal_audit_event_id": row.legal_audit_event_id,
            "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None,
        }

    @staticmethod
    def _claim_dict(row: IICSClaim) -> Dict[str, Any]:
        return {
            "id": str(row.id),
            "source_id": str(row.source_id),
            "claim": row.claim,
            "locator": row.locator,
            "publication_date": row.publication_date,
            "retrieved_at": row.retrieved_at.isoformat() if row.retrieved_at else None,
            "confidence": float(row.confidence or 0),
            "label": row.label,
        }

    async def register(
        self,
        url: str,
        *,
        source_type: str = "public_web",
        licence: Optional[str] = None,
        rights: Optional[Dict[str, bool]] = None,
        territory: Optional[str] = None,
        freshness_class: str = "documentation",
        reliability_score: float = 0.0,
        conditions: Optional[Iterable[str]] = None,
        legal_audit_event_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        result = await self.db.execute(select(IICSSource).where(IICSSource.url == url))
        existing = result.scalar_one_or_none()
        if existing:
            payload = self._row_dict(existing)
            payload["duplicate"] = True
            return payload
        row = IICSSource(
            url=url,
            domain=(urlparse(url).hostname or "").lower(),
            source_type=source_type,
            licence=licence,
            rights=dict(rights or {}),
            territory=territory,
            freshness_class=freshness_class,
            reliability_score=reliability_score,
            conditions=list(conditions or []),
            legal_audit_event_id=legal_audit_event_id,
            expires_at=expires_at,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        payload = self._row_dict(row)
        payload["duplicate"] = False
        return payload

    async def get(self, source_id: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(select(IICSSource).where(IICSSource.id == source_id))
        row = result.scalar_one_or_none()
        return self._row_dict(row) if row else None

    async def list(self, *, active_only: bool = False) -> List[Dict[str, Any]]:
        statement = select(IICSSource)
        if active_only:
            statement = statement.where(IICSSource.revoked_at.is_(None))
        result = await self.db.execute(statement.order_by(IICSSource.created_at.desc()))
        return [self._row_dict(row) for row in result.scalars().all()]

    @staticmethod
    def is_fresh(row: Any, now: Optional[datetime] = None) -> bool:
        """True when the source has not passed its class TTL or expiry."""
        if row.revoked_at:
            return False
        moment = now or datetime.now(timezone.utc)
        if row.expires_at:
            expiry = row.expires_at
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry <= moment:
                return False
        reference = row.last_checked_at or row.created_at
        if reference is None:
            return True
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=timezone.utc)
        ttl = timedelta(
            hours=FRESHNESS_TTL_HOURS.get(str(row.freshness_class), 720)
        )
        return bool(reference + ttl > moment)

    async def refresh_due(self) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(select(IICSSource).where(IICSSource.revoked_at.is_(None)))
        return [self._row_dict(row) for row in result.scalars().all() if not self.is_fresh(row, now)]

    async def touch(self, source_id: str, reliability_score: Optional[float] = None) -> bool:
        result = await self.db.execute(select(IICSSource).where(IICSSource.id == source_id))
        row: Any = result.scalar_one_or_none()
        if not row:
            return False
        row.last_checked_at = datetime.now(timezone.utc)
        if reliability_score is not None:
            row.reliability_score = reliability_score
        await self.db.commit()
        return True

    async def add_claim(
        self,
        source_id: str,
        claim: str,
        confidence: float,
        *,
        locator: Optional[str] = None,
        publication_date: Optional[str] = None,
        label: Optional[str] = None,
    ) -> Dict[str, Any]:
        source = await self.get(source_id)
        if not source:
            raise ValueError("source_not_found")
        if source.get("revoked_at"):
            raise PermissionError("source_revoked")
        if source["rights"].get("store") is False:
            raise PermissionError("store_right_denied")
        if not 0 <= confidence <= 1:
            raise ValueError("confidence_out_of_range")
        row = IICSClaim(
            source_id=source_id,
            claim=claim,
            locator=locator,
            publication_date=publication_date,
            confidence=confidence,
            label=label or label_for_confidence(confidence),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return self._claim_dict(row)

    async def claims(self, source_id: str) -> List[Dict[str, Any]]:
        result = await self.db.execute(
            select(IICSClaim).where(IICSClaim.source_id == source_id)
        )
        return [self._claim_dict(row) for row in result.scalars().all()]

    async def revoke(self, source_id: str) -> Dict[str, Any]:
        """Revoke a source and propagate 'outdated' to all derived claims."""
        result = await self.db.execute(select(IICSSource).where(IICSSource.id == source_id))
        row: Any = result.scalar_one_or_none()
        if not row:
            raise ValueError("source_not_found")
        row.revoked_at = datetime.now(timezone.utc)
        await self.db.execute(
            update(IICSClaim)
            .where(IICSClaim.source_id == source_id)
            .values(label="outdated")
        )
        await self.db.commit()
        await self.db.refresh(row)
        return self._row_dict(row)
