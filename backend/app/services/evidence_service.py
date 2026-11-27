"""P3 — Evidence and verification service.

Persistent evidence store, trusted source registry with credibility tracking,
and verification decay. Built on top of the existing HBI evidence grading
(hbi/evidence.py) and live evidence analysis (live_evidence_analysis.py).

Evidence is distinct from conclusions/beliefs:

* An ``EvidenceItem`` records an observation or source excerpt with provenance.
* A ``SourceRecord`` tracks a source's historical accuracy so credibility is
  empirically calibrated, not just a static prior.
* ``VerificationDecay`` schedules beliefs for re-verification as evidence
  ages or new contradictory evidence appears.

Nothing here is self-reported: verification always requires independent
evidence (external sources, cross-belief consistency, or experiment results).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import uuid
import loguru

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.memory import KnowledgeItem
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = loguru.logger

DEFAULT_VERIFICATION_INTERVAL_HOURS = 24
EVIDENCE_RETENTION_DAYS = 90


@dataclass
class EvidenceItem:
    """A single piece of evidence with provenance.

    Distinct from a belief: evidence is raw observation, belief is conclusion.
    """

    id: str
    source_id: str
    source_type: str  # e.g. "web_page", "api_response", "experiment", "document"
    locator: Optional[str]  # URL, file path, experiment id
    content: str  # the observed text/data
    collected_at: str
    credibility: float  # 0-1, from source registry
    evidence_type: str  # "observation", "measurement", "external_source", "experiment_result"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SourceRecord:
    """Tracked source with empirically calibrated credibility."""

    source_id: str
    source_type: str
    locator: Optional[str]
    reliability: float  # current calibrated reliability 0-1
    total_claims: int
    accurate_claims: int
    last_verified: Optional[str]
    first_seen: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def accuracy_rate(self) -> float:
        if self.total_claims == 0:
            return 0.0
        return self.accurate_claims / self.total_claims


class EvidenceService:
    """Persistent evidence and source-verification service.

    Uses the existing SQLAlchemy session pattern. Evidence items are stored
    as KnowledgeItem rows with topic="evidence" so they live in the same
    shared epistemic state as beliefs, but are typed distinctly.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Evidence ingestion
    # ------------------------------------------------------------------

    async def record_evidence(
        self,
        *,
        source_id: str,
        source_type: str,
        content: str,
        locator: Optional[str] = None,
        evidence_type: str = "observation",
        credibility: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvidenceItem:
        """Record a new evidence item with provenance.

        Credibility defaults to the source registry's current rating for
        this source_id/source_type, falling back to 0.5 if unknown.
        """
        if not content or not content.strip():
            raise ValueError("evidence content must not be empty")

        source = await self._get_or_create_source(source_id, source_type, locator)
        cred = credibility if credibility is not None else source.reliability

        item = KnowledgeItem(
            title=f"Evidence: {content[:80]}",
            content=content.strip(),
            source=source_id,
            confidence_level=max(0.0, min(1.0, cred)),
            topic="evidence",
            verification_status="unverified",
            metadata_={
                "evidence_type": evidence_type,
                "source_id": source_id,
                "source_type": source_type,
                "locator": locator,
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "source_reliability": source.reliability,
                **(metadata or {}),
            },
        )
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)

        return EvidenceItem(
            id=str(item.id),
            source_id=source_id,
            source_type=source_type,
            locator=locator,
            content=content.strip(),
            collected_at=item.metadata_.get("collected_at", ""),
            credibility=cred,
            evidence_type=evidence_type,
            metadata=item.metadata_ or {},
        )

    # ------------------------------------------------------------------
    # Source registry with empirical credibility
    # ------------------------------------------------------------------

    async def _get_or_create_source(
        self,
        source_id: str,
        source_type: str,
        locator: Optional[str] = None,
    ) -> SourceRecord:
        """Get or create a source record. Look for an existing evidence item
        from this source to infer its current reliability."""
        stmt = select(KnowledgeItem).where(
            KnowledgeItem.topic == "evidence",
            KnowledgeItem.source == source_id,
        ).order_by(KnowledgeItem.created_at.desc()).limit(1)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            meta = existing.metadata_ or {}
            reliability = float(meta.get("source_reliability", 0.5))
            total = int(meta.get("total_claims", 1))
            accurate = int(meta.get("accurate_claims", 0))
            return SourceRecord(
                source_id=source_id,
                source_type=source_type,
                locator=locator or meta.get("locator"),
                reliability=reliability,
                total_claims=total,
                accurate_claims=accurate,
                last_verified=meta.get("last_verified"),
                first_seen=existing.created_at.isoformat() if existing.created_at else "",
                metadata=meta,
            )

        return SourceRecord(
            source_id=source_id,
            source_type=source_type,
            locator=locator,
            reliability=0.5,  # neutral prior for unknown source
            total_claims=0,
            accurate_claims=0,
            last_verified=None,
            first_seen=datetime.now(timezone.utc).isoformat(),
        )

    async def update_source_accuracy(
        self,
        source_id: str,
        was_accurate: bool,
    ) -> SourceRecord:
        """Update a source's empirical accuracy after its claim is verified
        (or refuted) by independent evidence. This is how credibility becomes
        empirically calibrated rather than a static prior."""
        stmt = select(KnowledgeItem).where(
            KnowledgeItem.topic == "evidence",
            KnowledgeItem.source == source_id,
        ).order_by(KnowledgeItem.created_at.desc()).limit(1)
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing is None:
            # No evidence trail for this source; create a neutral record.
            meta = {
                "source_type": "unknown",
                "total_claims": 1,
                "accurate_claims": 1 if was_accurate else 0,
                "last_verified": datetime.now(timezone.utc).isoformat(),
                "locator": None,
                "source_reliability": 0.5 if was_accurate else 0.3,
            }
            item = KnowledgeItem(
                title=f"Source accuracy: {source_id}",
                content=f"Source {source_id} accuracy update",
                source=source_id,
                confidence_level=0.5,
                topic="source_accuracy",
                verification_status="verified",
                metadata_=meta,
            )
            self.db.add(item)
            await self.db.commit()
            return SourceRecord(
                source_id=source_id,
                source_type="unknown",
                locator=None,
                reliability=meta["source_reliability"],
                total_claims=1,
                accurate_claims=1 if was_accurate else 0,
                last_verified=meta["last_verified"],
                first_seen=datetime.now(timezone.utc).isoformat(),
            )

        meta = existing.metadata_ or {}
        total = int(meta.get("total_claims", 0)) + 1
        accurate = int(meta.get("accurate_claims", 0)) + (1 if was_accurate else 0)
        reliability = accurate / total if total > 0 else 0.5
        meta.update({
            "total_claims": total,
            "accurate_claims": accurate,
            "source_reliability": round(reliability, 3),
            "last_verified": datetime.now(timezone.utc).isoformat(),
        })
        existing.metadata_ = meta
        existing.confidence_level = reliability
        existing.last_reviewed_at = datetime.now(timezone.utc)
        await self.db.commit()

        return SourceRecord(
            source_id=source_id,
            source_type=str(meta.get("source_type", "unknown")),
            locator=meta.get("locator"),
            reliability=reliability,
            total_claims=total,
            accurate_claims=accurate,
            last_verified=meta["last_verified"],
            first_seen=existing.created_at.isoformat() if existing.created_at else "",
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # Verification decay
    # ------------------------------------------------------------------

    async def beliefs_due_for_reverification(
        self,
        *,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Return verified/disputed beliefs whose evidence has aged past the
        re-verification interval, or that have new contradictory evidence."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=DEFAULT_VERIFICATION_INTERVAL_HOURS)
        stmt = select(KnowledgeItem).where(
            KnowledgeItem.topic != "evidence",
            KnowledgeItem.verification_status.in_(("verified", "disputed")),
        ).order_by(KnowledgeItem.last_reviewed_at.asc().nullsfirst()).limit(limit)
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        due: List[Dict[str, Any]] = []
        for item in items:
            last_reviewed = item.last_reviewed_at
            needs_review = False
            reason = ""
            if last_reviewed is None:
                needs_review = True
                reason = "never_reviewed"
            elif last_reviewed.tzinfo is None:
                last_reviewed = last_reviewed.replace(tzinfo=timezone.utc)
            if last_reviewed < cutoff:
                needs_review = True
                reason = "verification_expired"
            if needs_review:
                due.append({
                    "belief_id": str(item.id),
                    "title": item.title,
                    "content": item.content,
                    "source": item.source,
                    "verification_status": item.verification_status,
                    "confidence_level": float(item.confidence_level) if item.confidence_level else 0.5,
                    "topic": item.topic,
                    "last_reviewed": last_reviewed.isoformat() if last_reviewed else None,
                    "reason": reason,
                })
        return due

    # ------------------------------------------------------------------
    # Evidence-to-belief linkage
    # ------------------------------------------------------------------

    async def link_evidence_to_belief(
        self,
        *,
        evidence_id: str,
        belief_id: str,
        relationship: str = "supports",
        strength: float = 1.0,
    ) -> Dict[str, Any]:
        """Record that a piece of evidence supports or contradicts a belief.

        Uses the existing memory_relationships table (already created in P0.1)
        but with evidence items as sources/targets.
        """
        from app.models.memory import MemoryRelationship
        import uuid as _uuid

        if evidence_id == belief_id:
            raise ValueError("evidence cannot link to itself")

        strength = max(0.0, min(1.0, float(strength)))

        # Verify both exist
        ev_result = await self.db.execute(
            select(KnowledgeItem).where(KnowledgeItem.id == evidence_id)
        )
        if ev_result.scalar_one_or_none() is None:
            raise ValueError(f"evidence not found: {evidence_id}")
        bl_result = await self.db.execute(
            select(KnowledgeItem).where(KnowledgeItem.id == belief_id)
        )
        if bl_result.scalar_one_or_none() is None:
            raise ValueError(f"belief not found: {belief_id}")

        rel = MemoryRelationship(
            source_memory_id=_uuid.UUID(evidence_id),
            target_memory_id=_uuid.UUID(belief_id),
            relationship_type=relationship,
            strength=strength,
        )
        self.db.add(rel)
        await self.db.commit()
        await self.db.refresh(rel)

        return {
            "id": str(rel.id),
            "evidence_id": evidence_id,
            "belief_id": belief_id,
            "relationship": relationship,
            "strength": strength,
        }
