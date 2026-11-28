"""Public records, vital events and estate research (OD-30).

Evidence-first and correction-friendly: records keep provenance, status and
confidence. Public availability never authorises bypassing access controls,
de-anonymisation, or treating an allegation as proof.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.publicrecords import PublicRecord, PublicSource, RecordRelationship
from app.models.security import AuditEvent

CATEGORIES = {
    "business", "government", "court", "property", "intellectual_property",
    "financial", "academic", "procurement", "professional", "electoral",
    "historical", "nonprofit", "vital_birth", "vital_adoption", "vital_marriage",
    "vital_divorce", "vital_death", "estate_probate", "inheritance", "insolvency",
    "unclaimed_property", "regulatory_enforcement", "security_public",
}

RESTRICTED_CATEGORIES = {
    "vital_birth", "vital_adoption", "vital_marriage", "vital_divorce",
    "estate_probate", "inheritance", "insolvency",
}

RELATION_TYPES = {"same_entity", "related_entity", "conflict", "correction"}
RECORD_STATUSES = {"verified", "self_reported", "uncertain", "allegation", "restricted"}


class PublicRecordsError(ValueError):
    pass


def _hash(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _confidence(value: Any) -> float:
    result = float(value)
    if result < 0 or result > 1:
        raise PublicRecordsError("confidence must be between 0 and 1")
    return result


class PublicRecordsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_source(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        for field in ("name", "jurisdiction", "category", "url"):
            if not payload.get(field):
                raise PublicRecordsError(f"{field} is required")
        access = payload.get("access_condition", "public")
        reliability = payload.get("reliability", "unverified")
        if access not in {"public", "requires_authority", "restricted", "paid", "unknown"}:
            raise PublicRecordsError("invalid access_condition")
        if reliability not in {"official", "independent", "self_reported", "unverified"}:
            raise PublicRecordsError("invalid reliability")

        existing = await self.db.execute(
            select(PublicSource).where(PublicSource.name == payload["name"])
        )
        if existing.scalar_one_or_none():
            raise PublicRecordsError("source already registered")

        source = PublicSource(
            name=payload["name"],
            jurisdiction=payload["jurisdiction"],
            category=payload["category"],
            url=payload["url"],
            access_condition=access,
            reliability=reliability,
            terms_url=payload.get("terms_url"),
            last_verified_at=payload.get("last_verified_at"),
        )
        self.db.add(source)
        self.db.add(
            AuditEvent(
                event_type="public_source_registered",
                actor=actor,
                target=source.name,
                details={"jurisdiction": source.jurisdiction, "access": access},
            )
        )
        await self.db.commit()
        await self.db.refresh(source)
        return self.source_dict(source)

    async def ingest(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        source_id = payload.get("source_id")
        result = await self.db.execute(
            select(PublicSource).where(PublicSource.id == source_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            raise PublicRecordsError("source not found")

        category = payload.get("category") or source.category
        if category not in CATEGORIES:
            raise PublicRecordsError(f"unsupported record category: {category}")
        if source.jurisdiction != payload.get("jurisdiction", source.jurisdiction):
            raise PublicRecordsError("record jurisdiction must match source jurisdiction")

        status = payload.get("status", "uncertain")
        if status not in RECORD_STATUSES:
            raise PublicRecordsError("invalid record status")
        facts = payload.get("facts") or {}
        if not isinstance(facts, dict):
            raise PublicRecordsError("facts must be an object")
        is_statistical = bool(payload.get("is_statistical", False))
        authority = payload.get("legal_authority_reference")

        if source.access_condition in {"requires_authority", "restricted", "paid"} and not authority:
            raise PublicRecordsError(
                f"source access is '{source.access_condition}'; legal authority reference is required. "
                "Access controls and paywalls must never be bypassed."
            )
        if (
            category in RESTRICTED_CATEGORIES
            and not is_statistical
            and not authority
            and not (category == "vital_death" and facts.get("public_notice") is True)
        ):
            raise PublicRecordsError(
                "this civil/estate category requires a legal authority reference "
                "unless it is statistical or an officially published death notice"
            )
        if status == "allegation" and facts.get("conviction") is True:
            raise PublicRecordsError("an allegation cannot be recorded as a conviction")

        confidence = _confidence(payload.get("confidence", 0.5))
        warnings: List[str] = []
        if status == "allegation":
            confidence = min(confidence, 0.5)
            warnings.append("allegation recorded as unverified; never proof of wrongdoing")
        if status == "self_reported":
            warnings.append("self-reported claim, not independently verified")

        record = PublicRecord(
            source_id=source.id,
            category=category,
            jurisdiction=payload.get("jurisdiction", source.jurisdiction),
            subject_name=payload.get("subject_name"),
            title=payload.get("title") or "Untitled record",
            published_at=payload.get("published_at"),
            retrieved_at=payload.get("retrieved_at") or datetime.now(timezone.utc),
            source_url=payload.get("source_url") or source.url,
            content_hash=_hash({"facts": facts, "title": payload.get("title")}),
            facts=facts,
            status=status,
            confidence=confidence,
            legal_authority_reference=authority,
            is_statistical=is_statistical,
        )
        self.db.add(record)
        self.db.add(
            AuditEvent(
                event_type="public_record_ingested",
                actor=actor,
                target=record.title[:200],
                details={"category": category, "status": status, "source_id": str(source.id)},
            )
        )
        await self.db.commit()
        await self.db.refresh(record)
        return {**self.record_dict(record), "warnings": warnings}

    async def search(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        query = select(PublicRecord)
        if filters.get("category"):
            query = query.where(PublicRecord.category == filters["category"])
        if filters.get("jurisdiction"):
            query = query.where(PublicRecord.jurisdiction == filters["jurisdiction"])
        if filters.get("subject_name"):
            query = query.where(
                PublicRecord.subject_name.ilike(f"%{filters['subject_name']}%")
            )
        if filters.get("status"):
            query = query.where(PublicRecord.status == filters["status"])
        limit = min(int(filters.get("limit", 50)), 200)
        result = await self.db.execute(query.order_by(PublicRecord.created_at.desc()).limit(limit))
        records = [self.record_dict(r) for r in result.scalars().all()]
        return {
            "records": records,
            "count": len(records),
            "note": "Status and confidence are evidence assessments, not identity proof.",
        }

    async def cross_reference(
        self,
        record_id: str,
        other_id: str,
        relation_type: str,
        evidence: Dict[str, Any],
        confidence: Any,
        actor: str = "sdk",
    ) -> Dict[str, Any]:
        if relation_type not in RELATION_TYPES:
            raise PublicRecordsError("invalid relation type")
        if not evidence:
            raise PublicRecordsError("evidence is required; records are never merged automatically")
        first = await self._record(record_id)
        second = await self._record(other_id)
        if first.id == second.id:
            raise PublicRecordsError("cannot relate a record to itself")
        link = RecordRelationship(
            from_record_id=first.id,
            to_record_id=second.id,
            relation_type=relation_type,
            evidence=evidence,
            confidence=_confidence(confidence),
        )
        self.db.add(link)
        self.db.add(
            AuditEvent(
                event_type="record_cross_referenced",
                actor=actor,
                target=record_id,
                details={"other_id": other_id, "relation": relation_type},
            )
        )
        await self.db.commit()
        await self.db.refresh(link)
        return self.relationship_dict(link)

    async def correct(
        self,
        record_id: str,
        facts: Dict[str, Any],
        reason: str,
        status: str,
        confidence: Any,
        actor: str = "sdk",
    ) -> Dict[str, Any]:
        if not reason:
            raise PublicRecordsError("a correction reason is required")
        original = await self._record(record_id)
        if status not in RECORD_STATUSES:
            raise PublicRecordsError("invalid record status")
        correction = PublicRecord(
            source_id=original.source_id,
            category=original.category,
            jurisdiction=original.jurisdiction,
            subject_name=original.subject_name,
            title=original.title,
            source_url=original.source_url,
            content_hash=_hash({"facts": facts, "correction_of": str(original.id)}),
            facts=facts,
            status=status,
            confidence=_confidence(confidence),
            legal_authority_reference=original.legal_authority_reference,
            is_statistical=original.is_statistical,
            is_correction=True,
            supersedes_id=original.id,
        )
        self.db.add(correction)
        await self.db.flush()
        self.db.add(
            RecordRelationship(
                from_record_id=correction.id,
                to_record_id=original.id,
                relation_type="correction",
                evidence={"reason": reason[:1000]},
                confidence=1.0,
            )
        )
        self.db.add(
            AuditEvent(
                event_type="public_record_corrected",
                actor=actor,
                target=record_id,
                details={"reason": reason[:500], "correction_id": str(correction.id)},
            )
        )
        await self.db.commit()
        await self.db.refresh(correction)
        return {**self.record_dict(correction), "original_preserved": True}

    async def relationships(self, record_id: str) -> Dict[str, Any]:
        await self._record(record_id)
        result = await self.db.execute(
            select(RecordRelationship).where(
                (RecordRelationship.from_record_id == record_id)
                | (RecordRelationship.to_record_id == record_id)
            )
        )
        return {
            "record_id": record_id,
            "relationships": [self.relationship_dict(r) for r in result.scalars().all()],
        }

    async def sources(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(PublicSource).order_by(PublicSource.name))
        return [self.source_dict(s) for s in result.scalars().all()]

    async def status(self) -> Dict[str, Any]:
        records = await self.db.execute(select(PublicRecord))
        sources = await self.db.execute(select(PublicSource))
        return {
            "records": len(records.scalars().all()),
            "sources": len(sources.scalars().all()),
            "principles": [
                "evidence_based", "dated", "traceable", "correctable",
                "allegations_not_proof", "no_identity_assumption",
            ],
        }

    async def _record(self, record_id: str) -> PublicRecord:
        result = await self.db.execute(
            select(PublicRecord).where(PublicRecord.id == record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise PublicRecordsError("record not found")
        return record

    @staticmethod
    def source_dict(source: PublicSource) -> Dict[str, Any]:
        return {
            "id": str(source.id),
            "name": source.name,
            "jurisdiction": source.jurisdiction,
            "category": source.category,
            "url": source.url,
            "access_condition": source.access_condition,
            "reliability": source.reliability,
            "terms_url": source.terms_url,
            "last_verified_at": source.last_verified_at.isoformat() if source.last_verified_at else None,
        }

    @staticmethod
    def record_dict(record: PublicRecord) -> Dict[str, Any]:
        return {
            "id": str(record.id),
            "source_id": str(record.source_id),
            "category": record.category,
            "jurisdiction": record.jurisdiction,
            "subject_name": record.subject_name,
            "title": record.title,
            "published_at": record.published_at.isoformat() if record.published_at else None,
            "retrieved_at": record.retrieved_at.isoformat() if record.retrieved_at else None,
            "source_url": record.source_url,
            "content_hash": record.content_hash,
            "facts": record.facts,
            "status": record.status,
            "confidence": record.confidence,
            "is_statistical": record.is_statistical,
            "is_correction": record.is_correction,
            "supersedes_id": str(record.supersedes_id) if record.supersedes_id else None,
        }

    @staticmethod
    def relationship_dict(link: RecordRelationship) -> Dict[str, Any]:
        return {
            "id": str(link.id),
            "from_record_id": str(link.from_record_id),
            "to_record_id": str(link.to_record_id),
            "relation_type": link.relation_type,
            "evidence": link.evidence,
            "confidence": link.confidence,
        }
