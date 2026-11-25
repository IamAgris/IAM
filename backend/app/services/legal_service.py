"""Autonomous legal learning, government monitoring and compliance (OD-31).

Legal research is not legal advice. IAM cannot decide an activity is lawful
just because no prohibition was found, cannot change its protected core, and
cannot bind itself legally. High-impact interpretations need qualified review.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.legal import (
    LegalChange,
    LegalImpact,
    LegalInstrument,
    LegalSource,
    LegalVersion,
)
from app.models.security import AuditEvent

STAGES = (
    "discover", "authenticate", "understand", "assess",
    "recommend", "authorise", "implement", "verify",
)
INSTRUMENT_TYPES = {
    "constitution", "legislation", "regulation", "court_judgment", "guidance",
    "policy", "bill", "draft_regulation", "treaty", "standard", "announcement",
}
INSTRUMENT_STATUSES = {"proposed", "draft", "enacted", "guidance", "announcement", "repealed"}
OBLIGATION_STATUSES = {"open", "in_progress", "completed", "overdue"}
PRIORITY = {"critical": "Immediate review", "important": "Creator notification", "informational": "Research update"}


class LegalError(ValueError):
    pass


def _hash(data: Any) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class LegalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_source(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        for field in ("name", "jurisdiction", "authority_type", "url"):
            if not payload.get(field):
                raise LegalError(f"{field} is required")
        if payload["authority_type"] not in {
            "government", "parliament", "court", "regulator", "central_bank",
            "tax_authority", "international", "security_authority",
        }:
            raise LegalError("invalid authority_type")
        existing = await self.db.execute(
            select(LegalSource).where(LegalSource.name == payload["name"])
        )
        if existing.scalar_one_or_none():
            raise LegalError("legal source already registered")
        source = LegalSource(
            name=payload["name"],
            jurisdiction=payload["jurisdiction"],
            authority_type=payload["authority_type"],
            url=payload["url"],
            feed_url=payload.get("feed_url"),
            reliability=payload.get("reliability", "official"),
            terms_url=payload.get("terms_url"),
        )
        self.db.add(source)
        self._audit(actor, "legal_source_registered", source.name, {"jurisdiction": source.jurisdiction})
        await self.db.commit()
        await self.db.refresh(source)
        return self.source_dict(source)

    async def record_instrument(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        source = await self._source(payload.get("source_id"))
        instrument_type = payload.get("instrument_type", "announcement")
        status = payload.get("status", "announcement")
        if instrument_type not in INSTRUMENT_TYPES or status not in INSTRUMENT_STATUSES:
            raise LegalError("invalid instrument type or status")
        content = payload.get("content") or {
            "title": payload.get("title"),
            "summary": payload.get("summary"),
            "official_url": payload.get("official_url") or source.url,
        }
        digest = _hash(content)
        instrument = LegalInstrument(
            source_id=source.id,
            jurisdiction=payload.get("jurisdiction", source.jurisdiction),
            title=payload.get("title") or "Untitled legal instrument",
            authority_name=payload.get("authority_name") or source.name,
            instrument_type=instrument_type,
            status=status,
            official_url=payload.get("official_url") or source.url,
            document_hash=digest,
            summary=payload.get("summary"),
            published_at=payload.get("published_at"),
            effective_at=payload.get("effective_at"),
        )
        self.db.add(instrument)
        await self.db.flush()
        self.db.add(
            LegalVersion(
                instrument_id=instrument.id,
                version_label="v1",
                document_hash=digest,
                content=content,
                valid_from=payload.get("effective_at") or payload.get("published_at"),
            )
        )
        self._audit(actor, "legal_instrument_recorded", instrument.title[:200], {"type": instrument_type})
        await self.db.commit()
        await self.db.refresh(instrument)
        return self.instrument_dict(instrument)

    async def amend_instrument(
        self, instrument_id: str, payload: Dict[str, Any], actor: str = "sdk"
    ) -> Dict[str, Any]:
        instrument = await self._instrument(instrument_id)
        content = payload.get("content") or {
            "title": payload.get("title") or instrument.title,
            "summary": payload.get("summary") or instrument.summary,
        }
        digest = _hash(content)
        versions = await self.db.execute(
            select(LegalVersion).where(LegalVersion.instrument_id == instrument.id)
        )
        next_version = len(versions.scalars().all()) + 1
        self.db.add(
            LegalVersion(
                instrument_id=instrument.id,
                version_label=f"v{next_version}",
                document_hash=digest,
                content=content,
                valid_from=payload.get("effective_at"),
            )
        )
        instrument.document_hash = digest
        instrument.status = payload.get("status", instrument.status)
        change = LegalChange(
            instrument_id=instrument.id,
            change_type="amendment",
            severity=payload.get("severity", "important"),
            evidence={"amendment": payload.get("reason", "new version recorded")},
        )
        self.db.add(change)
        await self.db.commit()
        await self.db.flush()
        self._audit(actor, "legal_amendment_recorded", instrument.title[:200], {"version": f"v{next_version}"})
        await self.db.commit()
        return {
            "instrument_id": str(instrument.id),
            "version": f"v{next_version}",
            "change_id": str(change.id),
            "previous_versions_preserved": True,
        }

    async def record_change(self, payload: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        instrument = await self._instrument(payload.get("instrument_id"))
        change_type = payload.get("change_type", "new")
        severity = payload.get("severity", "informational")
        if change_type not in {"new", "amendment", "repeal", "correction"}:
            raise LegalError("invalid change type")
        if severity not in PRIORITY:
            raise LegalError("invalid severity")
        evidence = payload.get("evidence") or {}
        if not evidence:
            raise LegalError("evidence is required before a change can be recorded")
        change = LegalChange(
            instrument_id=instrument.id,
            change_type=change_type,
            severity=severity,
            evidence=evidence,
        )
        self.db.add(change)
        self._audit(actor, "legal_change_discovered", instrument.title[:200], {"severity": severity})
        await self.db.commit()
        await self.db.refresh(change)
        return {**self.change_dict(change), "next_stage": "authenticate"}

    async def authenticate(self, change_id: str, actor: str = "sdk") -> Dict[str, Any]:
        change = await self._change(change_id)
        instrument = await self._instrument(str(change.instrument_id))
        source = await self._source(str(instrument.source_id))
        official_host = urlparse(instrument.official_url).netloc.lower()
        source_host = urlparse(source.url).netloc.lower()
        matches = bool(official_host) and official_host == source_host
        authenticated = matches and source.reliability == "official"
        evidence = dict(change.evidence or {})
        evidence["authentication"] = {
            "official_host_matches_source": matches,
            "source_reliability": source.reliability,
            "confidence": "document_host_and_source_reliability_only",
        }
        change.evidence = evidence
        change.authenticated = authenticated
        change.lifecycle_stage = "authenticate"
        await self.db.commit()
        return {
            "change_id": change_id,
            "authenticated": authenticated,
            "confidence": "best_effort_not_certainty",
            "next_stage": "understand",
        }

    async def understand(self, change_id: str, summary: str, actor: str = "sdk") -> Dict[str, Any]:
        change = await self._change(change_id)
        if not summary:
            raise LegalError("summary is required")
        if change.lifecycle_stage not in ("authenticate", "understand"):
            raise LegalError("change must be authenticated before it can be understood")
        evidence = dict(change.evidence or {})
        evidence["understanding"] = summary[:2000]
        change.evidence = evidence
        change.lifecycle_stage = "understand"
        await self.db.commit()
        return {"change_id": change_id, "lifecycle_stage": change.lifecycle_stage}

    async def assess(self, change_id: str, impacts: List[Dict[str, Any]], actor: str = "sdk") -> Dict[str, Any]:
        change = await self._change(change_id)
        if change.lifecycle_stage not in ("understand", "assess"):
            raise LegalError("change must be understood before assessment")
        if not impacts:
            raise LegalError("at least one impact assessment is required")
        created = []
        high_risk = False
        for item in impacts:
            risk = item.get("risk_level", "low")
            if risk not in {"low", "medium", "high", "critical"}:
                raise LegalError("invalid risk_level")
            high_risk = high_risk or risk in {"high", "critical"}
            impact = LegalImpact(
                change_id=change.id,
                affected_system=item.get("affected_system", "unspecified"),
                assessment=item.get("assessment", ""),
                risk_level=risk,
                recommendation=item.get("recommendation", ""),
                obligations=item.get("obligations") or [],
                evidence=item.get("evidence") or [],
            )
            self.db.add(impact)
            created.append(impact)
        await self.db.flush()
        change.lifecycle_stage = "assess"
        self._audit(actor, "legal_impact_recorded", change_id, {"impacts": len(created)})
        await self.db.commit()
        return {
            "change_id": change_id,
            "impacts": [str(i.id) for i in created],
            "professional_review_required": high_risk,
            "note": "legal_research_not_legal_advice",
            "next_stage": "recommend",
        }

    async def recommend(self, change_id: str, recommendations: List[str], actor: str = "sdk") -> Dict[str, Any]:
        change = await self._change(change_id)
        if change.lifecycle_stage not in ("assess", "recommend"):
            raise LegalError("change must be assessed before recommendations")
        evidence = dict(change.evidence or {})
        evidence["recommendations"] = recommendations[:50]
        change.evidence = evidence
        change.lifecycle_stage = "recommend"
        await self.db.commit()
        return {"change_id": change_id, "lifecycle_stage": "recommend"}

    async def authorise(
        self,
        change_id: str,
        creator_approval_reference: str,
        professional_review_reference: Optional[str] = None,
        actor: str = "creator",
    ) -> Dict[str, Any]:
        change = await self._change(change_id)
        if change.lifecycle_stage != "recommend":
            raise LegalError("change must reach the recommend stage before authorisation")
        if not creator_approval_reference:
            raise LegalError("creator approval reference is required; IAM cannot self-authorise")
        impacts = await self.db.execute(
            select(LegalImpact).where(LegalImpact.change_id == change.id)
        )
        high_risk = any(i.risk_level in {"high", "critical"} for i in impacts.scalars().all())
        if high_risk and not professional_review_reference:
            raise LegalError("high-impact legal conclusions require qualified professional review")
        change.creator_approval_reference = creator_approval_reference
        change.professional_review_reference = professional_review_reference
        change.lifecycle_stage = "authorise"
        self._audit(actor, "legal_change_authorised", change_id, {"reference": creator_approval_reference[:100]})
        await self.db.commit()
        return {"change_id": change_id, "lifecycle_stage": "authorise"}

    async def implement(self, change_id: str, evidence: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        change = await self._change(change_id)
        if change.lifecycle_stage != "authorise":
            raise LegalError("change must be authorised before implementation")
        if not evidence:
            raise LegalError("implementation evidence is required")
        data = dict(change.evidence or {})
        data["implementation"] = evidence
        change.evidence = data
        change.implemented_at = datetime.now(timezone.utc)
        change.lifecycle_stage = "implement"
        await self.db.commit()
        return {"change_id": change_id, "lifecycle_stage": "implement"}

    async def verify(self, change_id: str, evidence: Dict[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        change = await self._change(change_id)
        if change.lifecycle_stage != "implement":
            raise LegalError("change must be implemented before verification")
        if not evidence:
            raise LegalError("verification evidence is required")
        data = dict(change.evidence or {})
        data["verification"] = evidence
        change.evidence = data
        change.verified_at = datetime.now(timezone.utc)
        change.lifecycle_stage = "verify"
        self._audit(actor, "legal_change_verified", change_id, {})
        await self.db.commit()
        return {
            "change_id": change_id,
            "lifecycle_stage": "verify",
            "claim": "compliance_verified_for_recorded_scope_only",
        }

    async def update_obligation(
        self,
        impact_id: str,
        obligation_id: str,
        status: str,
        evidence: Dict[str, Any],
        actor: str = "sdk",
    ) -> Dict[str, Any]:
        if status not in OBLIGATION_STATUSES:
            raise LegalError("invalid obligation status")
        result = await self.db.execute(
            select(LegalImpact).where(LegalImpact.id == impact_id)
        )
        impact = result.scalar_one_or_none()
        if not impact:
            raise LegalError("impact not found")
        obligations = list(impact.obligations or [])
        target = next((o for o in obligations if o.get("id") == obligation_id), None)
        if not target:
            raise LegalError("obligation not found")
        target["status"] = status
        target["updated_at"] = datetime.now(timezone.utc).isoformat()
        evidence_list = list(impact.evidence or [])
        evidence_list.append({"obligation_id": obligation_id, "hash": _hash(evidence), **evidence})
        impact.evidence = evidence_list
        self._audit(actor, "legal_obligation_updated", obligation_id, {"status": status})
        await self.db.commit()
        return {"obligation": target, "evidence_recorded": True}

    async def check_source(self, source_id: str, content: Optional[str] = None) -> Dict[str, Any]:
        source = await self._source(source_id)
        if content is None:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(source.feed_url or source.url)
                    content = response.text
            except httpx.HTTPError as exc:
                raise LegalError(f"official source unreachable: {exc}") from exc
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        changed = source.last_content_hash is not None and source.last_content_hash != digest
        source.last_content_hash = digest
        source.last_checked_at = datetime.now(timezone.utc)
        await self.db.commit()
        return {
            "source_id": source_id,
            "changed": changed,
            "first_observation": source.last_content_hash is None,
            "content_hash": digest,
            "note": "a hash change signals a possible new publication; it is not proof of a legal change",
        }

    async def alerts(self, severity: Optional[str] = None) -> Dict[str, Any]:
        query = select(LegalChange)
        if severity:
            query = query.where(LegalChange.severity == severity)
        result = await self.db.execute(query.order_by(LegalChange.created_at.desc()))
        changes = result.scalars().all()
        return {
            "alerts": [
                {
                    "id": str(c.id),
                    "severity": c.severity,
                    "priority": PRIORITY[c.severity],
                    "stage": c.lifecycle_stage,
                    "authenticated": c.authenticated,
                    "creator_approval_reference": c.creator_approval_reference,
                    "professional_review_reference": c.professional_review_reference,
                }
                for c in changes
            ]
        }

    async def sources(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(LegalSource).order_by(LegalSource.name))
        return [self.source_dict(source) for source in result.scalars().all()]

    async def status(self) -> Dict[str, Any]:
        changes = (await self.db.execute(select(LegalChange))).scalars().all()
        instruments = (await self.db.execute(select(LegalInstrument))).scalars().all()
        sources = (await self.db.execute(select(LegalSource))).scalars().all()
        return {
            "sources": len(sources),
            "instruments": len(instruments),
            "changes": len(changes),
            "by_stage": {stage: sum(1 for c in changes if c.lifecycle_stage == stage) for stage in STAGES},
            "claim": "legal_research_not_legal_advice",
            "boundaries": [
                "no_self_authorisation", "no_binding_commitments",
                "no_protected_core_changes", "professional_review_for_high_impact",
            ],
        }

    def _audit(self, actor: str, event_type: str, target: str, details: Dict[str, Any]) -> None:
        self.db.add(AuditEvent(event_type=event_type, actor=actor, target=target, details=details))

    async def _source(self, source_id: Any) -> LegalSource:
        result = await self.db.execute(
            select(LegalSource).where(LegalSource.id == source_id)
        )
        source = result.scalar_one_or_none()
        if not source:
            raise LegalError("legal source not found")
        return source

    async def _instrument(self, instrument_id: Any) -> LegalInstrument:
        result = await self.db.execute(
            select(LegalInstrument).where(LegalInstrument.id == instrument_id)
        )
        instrument = result.scalar_one_or_none()
        if not instrument:
            raise LegalError("legal instrument not found")
        return instrument

    async def _change(self, change_id: str) -> LegalChange:
        result = await self.db.execute(
            select(LegalChange).where(LegalChange.id == change_id)
        )
        change = result.scalar_one_or_none()
        if not change:
            raise LegalError("legal change not found")
        return change

    @staticmethod
    def source_dict(source: LegalSource) -> Dict[str, Any]:
        return {
            "id": str(source.id),
            "name": source.name,
            "jurisdiction": source.jurisdiction,
            "authority_type": source.authority_type,
            "url": source.url,
            "feed_url": source.feed_url,
            "reliability": source.reliability,
            "is_active": source.is_active,
            "last_checked_at": source.last_checked_at.isoformat() if source.last_checked_at else None,
        }

    @staticmethod
    def instrument_dict(instrument: LegalInstrument) -> Dict[str, Any]:
        return {
            "id": str(instrument.id),
            "source_id": str(instrument.source_id),
            "jurisdiction": instrument.jurisdiction,
            "title": instrument.title,
            "authority_name": instrument.authority_name,
            "instrument_type": instrument.instrument_type,
            "status": instrument.status,
            "official_url": instrument.official_url,
            "document_hash": instrument.document_hash,
            "published_at": instrument.published_at.isoformat() if instrument.published_at else None,
            "effective_at": instrument.effective_at.isoformat() if instrument.effective_at else None,
        }

    @staticmethod
    def change_dict(change: LegalChange) -> Dict[str, Any]:
        return {
            "id": str(change.id),
            "instrument_id": str(change.instrument_id),
            "change_type": change.change_type,
            "severity": change.severity,
            "lifecycle_stage": change.lifecycle_stage,
            "authenticated": change.authenticated,
            "evidence": change.evidence,
        }
