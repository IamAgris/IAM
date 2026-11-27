"""Versioned per-site policy store and privacy lifecycle (§2.8).

robots.txt is a crawling signal, never permission. Snapshots carry TTL and a
content hash so changes can be detected and cached decisions invalidated.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.iics import IICSSitePolicy, IICSPrivacyRecord

PRIVACY_KINDS = frozenset(
    {"dsar_access", "dsar_erasure", "consent_withdrawal", "transfer_assessment"}
)
TRANSFER_EVIDENCE = frozenset({"scc", "adequacy", "tia"})


def policy_hash(robots: str, terms: str) -> str:
    return hashlib.sha256(f"{robots}\0{terms}".encode("utf-8")).hexdigest()


class SitePolicyStore:
    """Domain policy snapshots with TTL, change detection and cache evidence."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _row_dict(row: IICSSitePolicy) -> Dict[str, Any]:
        return {
            "domain": row.domain,
            "robots_text": row.robots_text,
            "terms_text": row.terms_text,
            "content_hash": row.content_hash,
            "ttl_hours": int(row.ttl_hours),
            "source_url": row.source_url,
            "notes": row.notes,
            "snapshot_at": row.snapshot_at.isoformat() if row.snapshot_at else None,
        }

    async def record(
        self,
        domain: str,
        robots_text: str = "",
        terms_text: str = "",
        *,
        ttl_hours: int = 720,
        source_url: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        if ttl_hours < 1:
            raise ValueError("ttl_hours must be positive")
        clean_domain = domain.strip().lower().rstrip(".")
        digest = policy_hash(robots_text, terms_text)
        result = await self.db.execute(
            select(IICSSitePolicy).where(IICSSitePolicy.domain == clean_domain)
        )
        row = cast(Any, result.scalar_one_or_none())
        changed = bool(row and row.content_hash != digest)
        if row:
            row.robots_text = robots_text
            row.terms_text = terms_text
            row.content_hash = digest
            row.ttl_hours = ttl_hours
            row.source_url = source_url
            row.notes = notes
            row.snapshot_at = datetime.now(timezone.utc)
        else:
            row = IICSSitePolicy(
                domain=clean_domain,
                robots_text=robots_text,
                terms_text=terms_text,
                content_hash=digest,
                ttl_hours=ttl_hours,
                source_url=source_url,
                notes=notes,
            )
            self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        payload = self._row_dict(row)
        payload["changed"] = changed
        return payload

    async def get(self, domain: str) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(IICSSitePolicy).where(IICSSitePolicy.domain == domain.strip().lower().rstrip("."))
        )
        row = result.scalar_one_or_none()
        return self._row_dict(row) if row else None

    async def is_stale(self, domain: str, now: Optional[datetime] = None) -> bool:
        row = await self.get(domain)
        if not row:
            return True
        moment = now or datetime.now(timezone.utc)
        snapshot = datetime.fromisoformat(str(row["snapshot_at"]))
        if snapshot.tzinfo is None:
            snapshot = snapshot.replace(tzinfo=timezone.utc)
        return snapshot + timedelta(hours=int(row["ttl_hours"])) <= moment

    async def changed(self, domain: str, robots_text: str, terms_text: str) -> bool:
        current = await self.get(domain)
        return bool(current and current["content_hash"] != policy_hash(robots_text, terms_text))

    async def list_stale(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(IICSSitePolicy))
        now = datetime.now(timezone.utc)
        stale: List[Dict[str, Any]] = []
        for row in result.scalars().all():
            payload = self._row_dict(row)
            snapshot = datetime.fromisoformat(str(payload["snapshot_at"]))
            if snapshot.tzinfo is None:
                snapshot = snapshot.replace(tzinfo=timezone.utc)
            if snapshot + timedelta(hours=int(payload["ttl_hours"])) <= now:
                stale.append(payload)
        return stale


class PrivacyLifecycle:
    """DSAR/consent/transfer records with evidence-gated transfer decisions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def open(
        self,
        kind: str,
        subject_ref: str,
        *,
        jurisdiction: Optional[str] = None,
        details: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        if kind not in PRIVACY_KINDS:
            raise ValueError("unknown privacy record kind")
        row = IICSPrivacyRecord(
            kind=kind,
            subject_ref=subject_ref,
            jurisdiction=jurisdiction,
            status="open",
            details=dict(details or {}),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return {"id": str(row.id), "kind": row.kind, "status": row.status}

    async def resolve(
        self,
        record_id: str,
        evidence: Mapping[str, Any],
        *,
        status: str = "resolved",
    ) -> bool:
        if status not in {"resolved", "refused", "in_progress"}:
            raise ValueError("unknown privacy status")
        result = await self.db.execute(
            update(IICSPrivacyRecord)
            .where(IICSPrivacyRecord.id == record_id)
            .values(status=status, evidence=dict(evidence), resolved_at=datetime.now(timezone.utc))
        )
        await self.db.commit()
        return bool(cast(Any, result).rowcount)

    async def transfer_permitted(self, subject_ref: str, jurisdiction: str) -> bool:
        """Fail closed unless a resolved assessment carries transfer evidence."""
        result = await self.db.execute(
            select(IICSPrivacyRecord).where(
                IICSPrivacyRecord.kind == "transfer_assessment",
                IICSPrivacyRecord.subject_ref == subject_ref,
                IICSPrivacyRecord.status == "resolved",
            )
        )
        for row in result.scalars().all():
            if row.jurisdiction and row.jurisdiction.upper() != jurisdiction.upper():
                continue
            evidence = {str(key).lower() for key in (cast(Any, row.evidence) or {})}
            if evidence & TRANSFER_EVIDENCE:
                return True
        return False
