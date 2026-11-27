"""Storage adapters for IPLCI.

The decision logic is storage-agnostic: ``MemoryStore`` supports deterministic
tests and embedded use, ``SQLStore`` persists the same record shape to the
``ip_legal_*`` tables. Never put permission decisions in the adapters.
"""

from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol, Type

from sqlalchemy import DateTime, JSON, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ip_legal import (
    IPLegalAssessment,
    IPLegalAuditEvent,
    IPLegalCollectionCheck,
    IPLegalComplianceDeadline,
    IPLegalContinuityRecord,
    IPLegalDatasetProvenance,
    IPLegalDependency,
    IPLegalBusinessReview,
    IPLegalDesignRight,
    IPLegalDisputeCase,
    IPLegalEthicsReview,
    IPLegalEvidenceRecord,
    IPLegalIncidentCase,
    IPLegalLegalHold,
    IPLegalRightsContact,
    IPLegalIPAsset,
    IPLegalJurisdictionRule,
    IPLegalKnowledgeVerification,
    IPLegalLicence,
    IPLegalModelLineage,
    IPLegalObligation,
    IPLegalOfficialSource,
    IPLegalParty,
    IPLegalPatent,
    IPLegalPolicy,
    IPLegalPermission,
    IPLegalPrivacyRecord,
    IPLegalRiskDecision,
    IPLegalSbom,
    IPLegalSource,
    IPLegalTrainingApproval,
    IPLegalTrademark,
)


class Store(Protocol):
    async def get_source(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_source(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_sources(self) -> List[Dict[str, Any]]: ...
    async def get_permission(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_permission(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_permissions(self, source_id: str) -> List[Dict[str, Any]]: ...
    async def get_assessment(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_asset(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_asset(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_assets(self) -> List[Dict[str, Any]]: ...
    async def get_dataset(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_dataset(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def last_sequence(self) -> int: ...
    async def last_hash(self) -> str: ...
    async def append_audit(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_audit(self, limit: int = 100) -> List[Dict[str, Any]]: ...
    async def commit(self) -> None: ...
    async def put_trademark(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_trademarks(self) -> List[Dict[str, Any]]: ...
    async def put_patent(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_patents(self) -> List[Dict[str, Any]]: ...
    async def put_design(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_designs(self) -> List[Dict[str, Any]]: ...
    async def put_dependency(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_dependencies(self, project_id: str) -> List[Dict[str, Any]]: ...
    async def put_sbom(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_sbom(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_risk(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_risk(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_collection_check(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_collection_check(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_privacy(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_privacy(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_training_approval(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_training_approval(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_lineage(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_lineage(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_jurisdiction_rule(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_jurisdiction_rules(self, jurisdiction: str) -> List[Dict[str, Any]]: ...
    async def put_official_source(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_official_sources(self) -> List[Dict[str, Any]]: ...
    async def put_knowledge_verification(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_knowledge_verification(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_obligation(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_obligations(self) -> List[Dict[str, Any]]: ...
    async def put_business_review(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_business_review(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_ethics_review(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_ethics_review(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_dispute(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_dispute(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def list_disputes(self) -> List[Dict[str, Any]]: ...
    async def put_incident(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_incident(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_legal_hold(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_legal_hold(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_rights_contact(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_rights_contacts(self) -> List[Dict[str, Any]]: ...
    async def put_deadline(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def list_deadlines(self) -> List[Dict[str, Any]]: ...
    async def put_evidence(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_evidence(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def list_evidence(self) -> List[Dict[str, Any]]: ...
    async def put_continuity(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_continuity(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def put_policy(self, data: Dict[str, Any]) -> Dict[str, Any]: ...
    async def get_policy(self, record_id: str) -> Optional[Dict[str, Any]]: ...
    async def active_policy(self) -> Optional[Dict[str, Any]]: ...


class MemoryStore:
    """Deterministic in-process store used by tests and embedded governance."""

    def __init__(self) -> None:
        self._sources: Dict[str, Dict[str, Any]] = {}
        self._permissions: Dict[str, Dict[str, Any]] = {}
        self._assessments: Dict[str, Dict[str, Any]] = {}
        self._assets: Dict[str, Dict[str, Any]] = {}
        self._datasets: Dict[str, Dict[str, Any]] = {}
        self._audit: List[Dict[str, Any]] = []
        self._trademarks: Dict[str, Dict[str, Any]] = {}
        self._patents: Dict[str, Dict[str, Any]] = {}
        self._designs: Dict[str, Dict[str, Any]] = {}
        self._dependencies: Dict[str, Dict[str, Any]] = {}
        self._sboms: Dict[str, Dict[str, Any]] = {}
        self._risks: Dict[str, Dict[str, Any]] = {}
        self._collection_checks: Dict[str, Dict[str, Any]] = {}
        self._privacy: Dict[str, Dict[str, Any]] = {}
        self._training_approvals: Dict[str, Dict[str, Any]] = {}
        self._lineages: Dict[str, Dict[str, Any]] = {}
        self._jurisdiction_rules: Dict[str, Dict[str, Any]] = {}
        self._official_sources: Dict[str, Dict[str, Any]] = {}
        self._knowledge_verifications: Dict[str, Dict[str, Any]] = {}
        self._obligations: Dict[str, Dict[str, Any]] = {}
        self._business_reviews: Dict[str, Dict[str, Any]] = {}
        self._ethics_reviews: Dict[str, Dict[str, Any]] = {}
        self._disputes: Dict[str, Dict[str, Any]] = {}
        self._incidents: Dict[str, Dict[str, Any]] = {}
        self._legal_holds: Dict[str, Dict[str, Any]] = {}
        self._rights_contacts: Dict[str, Dict[str, Any]] = {}
        self._deadlines: Dict[str, Dict[str, Any]] = {}
        self._evidence: Dict[str, Dict[str, Any]] = {}
        self._continuity: Dict[str, Dict[str, Any]] = {}
        self._policies: Dict[str, Dict[str, Any]] = {}

    async def _put_generic(self, bucket: Dict[str, Dict[str, Any]], data: Dict[str, Any]) -> Dict[str, Any]:
        record = copy.deepcopy(data)
        bucket[str(record["id"])] = record
        return copy.deepcopy(record)

    async def commit(self) -> None:
        return None

    async def get_source(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._sources.get(record_id))
    async def put_source(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record = copy.deepcopy(data)
        self._sources[str(record["id"])] = record
        return copy.deepcopy(record)
    async def list_sources(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(list(self._sources.values()))

    async def get_permission(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._permissions.get(record_id))
    async def put_permission(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record = copy.deepcopy(data)
        self._permissions[str(record["id"])] = record
        return copy.deepcopy(record)
    async def list_permissions(self, source_id: str) -> List[Dict[str, Any]]:
        return copy.deepcopy([
            item for item in self._permissions.values() if item.get("source_id") == source_id
        ])

    async def get_assessment(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._assessments.get(record_id))
    async def put_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record = copy.deepcopy(data)
        self._assessments[str(record["id"])] = record
        return copy.deepcopy(record)

    async def get_asset(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._assets.get(record_id))
    async def put_asset(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record = copy.deepcopy(data)
        self._assets[str(record["id"])] = record
        return copy.deepcopy(record)
    async def list_assets(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(list(self._assets.values()))

    async def get_dataset(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._datasets.get(record_id))
    async def put_dataset(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record = copy.deepcopy(data)
        self._datasets[str(record["id"])] = record
        return copy.deepcopy(record)

    async def put_trademark(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._trademarks, data)
    async def list_trademarks(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(list(self._trademarks.values()))

    async def put_patent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._patents, data)
    async def list_patents(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(list(self._patents.values()))

    async def put_design(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._designs, data)
    async def list_designs(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(list(self._designs.values()))

    async def put_dependency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._dependencies, data)
    async def list_dependencies(self, project_id: str) -> List[Dict[str, Any]]:
        return copy.deepcopy([
            item for item in self._dependencies.values() if item.get("project_id") == project_id
        ])

    async def put_sbom(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._sboms, data)
    async def get_sbom(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._sboms.get(record_id))

    async def put_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._risks, data)
    async def get_risk(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._risks.get(record_id))

    async def put_collection_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._collection_checks, data)
    async def get_collection_check(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._collection_checks.get(record_id))

    async def put_privacy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._privacy, data)
    async def get_privacy(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._privacy.get(record_id))

    async def put_training_approval(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._training_approvals, data)
    async def get_training_approval(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._training_approvals.get(record_id))

    async def put_lineage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._lineages, data)
    async def get_lineage(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._lineages.get(record_id))

    async def put_jurisdiction_rule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._jurisdiction_rules, data)
    async def list_jurisdiction_rules(self, jurisdiction: str) -> List[Dict[str, Any]]:
        return copy.deepcopy([
            item for item in self._jurisdiction_rules.values()
            if item.get("jurisdiction") == jurisdiction
        ])

    async def put_official_source(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._official_sources, data)
    async def list_official_sources(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(list(self._official_sources.values()))

    async def put_knowledge_verification(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._knowledge_verifications, data)
    async def get_knowledge_verification(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._knowledge_verifications.get(record_id))

    async def put_obligation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._obligations, data)
    async def list_obligations(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(list(self._obligations.values()))

    async def put_business_review(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._business_reviews, data)
    async def get_business_review(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._business_reviews.get(record_id))

    async def put_ethics_review(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._ethics_reviews, data)
    async def get_ethics_review(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._ethics_reviews.get(record_id))

    async def put_dispute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._disputes, data)
    async def get_dispute(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._disputes.get(record_id))
    async def list_disputes(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(list(self._disputes.values()))

    async def put_incident(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._incidents, data)
    async def get_incident(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._incidents.get(record_id))

    async def put_legal_hold(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._legal_holds, data)
    async def get_legal_hold(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._legal_holds.get(record_id))

    async def put_rights_contact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._rights_contacts, data)
    async def list_rights_contacts(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(list(self._rights_contacts.values()))

    async def put_deadline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._deadlines, data)
    async def list_deadlines(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(list(self._deadlines.values()))

    async def put_evidence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._evidence, data)
    async def get_evidence(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._evidence.get(record_id))
    async def list_evidence(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(list(self._evidence.values()))

    async def put_continuity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._continuity, data)
    async def get_continuity(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._continuity.get(record_id))

    async def put_policy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put_generic(self._policies, data)
    async def get_policy(self, record_id: str) -> Optional[Dict[str, Any]]:
        return copy.deepcopy(self._policies.get(record_id))
    async def active_policy(self) -> Optional[Dict[str, Any]]:
        active = [
            item for item in self._policies.values()
            if str(item.get("status")) == "active"
        ]
        return copy.deepcopy(active[-1]) if active else None

    async def last_sequence(self) -> int:
        return len(self._audit)
    async def last_hash(self) -> str:
        return str(self._audit[-1]["event_hash"]) if self._audit else "0" * 64
    async def append_audit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        record = copy.deepcopy(data)
        self._audit.append(record)
        return copy.deepcopy(record)
    async def list_audit(self, limit: int = 100) -> List[Dict[str, Any]]:
        # Most recent first, matching SQLStore and the audit API contract.
        return copy.deepcopy(list(reversed(self._audit[-limit:])))


def _uuid(value: Any) -> uuid.UUID:
    return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def _to_dict(row: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if value is None:
            result[column.name] = None
        elif isinstance(value, datetime):
            result[column.name] = value.isoformat()
        elif isinstance(value, uuid.UUID):
            result[column.name] = str(value)
        else:
            result[column.name] = value
    return result


def _column_value(column: Any, value: Any) -> Any:
    if value is None:
        return None
    if isinstance(column.type, PGUUID):
        return _uuid(value)
    if isinstance(column.type, DateTime):
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if isinstance(column.type, JSON):
        return value
    return value


class SQLStore:
    """Postgres/SQLAlchemy-backed store for production use."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def commit(self) -> None:
        await self.db.commit()

    async def _get(self, model: Type[Any], record_id: str) -> Optional[Dict[str, Any]]:
        try:
            key = _uuid(record_id)
        except (ValueError, AttributeError, TypeError):
            return None
        row = (
            await self.db.execute(select(model).where(model.id == key))
        ).scalar_one_or_none()
        return _to_dict(row) if row else None

    async def _put(self, model: Type[Any], data: Dict[str, Any]) -> Dict[str, Any]:
        record_id = data.get("id")
        row = await self._get(model, record_id) if record_id else None
        columns = {column.name: column for column in model.__table__.columns}
        if row is None:
            row = model()
            if record_id:
                row.id = _uuid(record_id)
            self.db.add(row)
        for name, value in data.items():
            if name in ("id", "created_at", "updated_at") or name not in columns:
                continue
            setattr(row, name, _column_value(columns[name], value))
        await self.db.flush()
        await self.db.refresh(row)
        return _to_dict(row)

    async def _list(self, model: Type[Any], order_by: Any = None) -> List[Dict[str, Any]]:
        stmt = select(model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        rows = (await self.db.execute(stmt)).scalars().all()
        return [_to_dict(row) for row in rows]

    async def get_source(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalSource, record_id)
    async def put_source(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalSource, data)
    async def list_sources(self) -> List[Dict[str, Any]]:
        return await self._list(IPLegalSource)

    async def get_permission(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalPermission, record_id)
    async def put_permission(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalPermission, data)
    async def list_permissions(self, source_id: str) -> List[Dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(IPLegalPermission).where(IPLegalPermission.source_id == _uuid(source_id))
            )
        ).scalars().all()
        return [_to_dict(row) for row in rows]

    async def get_assessment(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalAssessment, record_id)
    async def put_assessment(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalAssessment, data)

    async def get_asset(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalIPAsset, record_id)
    async def put_asset(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalIPAsset, data)
    async def list_assets(self) -> List[Dict[str, Any]]:
        return await self._list(IPLegalIPAsset)

    async def get_dataset(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalDatasetProvenance, record_id)
    async def put_dataset(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalDatasetProvenance, data)

    async def put_trademark(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalTrademark, data)
    async def list_trademarks(self) -> List[Dict[str, Any]]:
        return await self._list(IPLegalTrademark)

    async def put_patent(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalPatent, data)
    async def list_patents(self) -> List[Dict[str, Any]]:
        return await self._list(IPLegalPatent)

    async def put_design(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalDesignRight, data)
    async def list_designs(self) -> List[Dict[str, Any]]:
        return await self._list(IPLegalDesignRight)

    async def put_dependency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalDependency, data)
    async def list_dependencies(self, project_id: str) -> List[Dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(IPLegalDependency).where(IPLegalDependency.project_id == project_id)
            )
        ).scalars().all()
        return [_to_dict(row) for row in rows]

    async def put_sbom(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalSbom, data)
    async def get_sbom(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalSbom, record_id)

    async def put_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalRiskDecision, data)
    async def get_risk(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalRiskDecision, record_id)

    async def put_collection_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalCollectionCheck, data)
    async def get_collection_check(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalCollectionCheck, record_id)

    async def put_privacy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalPrivacyRecord, data)
    async def get_privacy(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalPrivacyRecord, record_id)

    async def put_training_approval(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalTrainingApproval, data)
    async def get_training_approval(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalTrainingApproval, record_id)

    async def put_lineage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalModelLineage, data)
    async def get_lineage(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalModelLineage, record_id)

    async def put_jurisdiction_rule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalJurisdictionRule, data)
    async def list_jurisdiction_rules(self, jurisdiction: str) -> List[Dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(IPLegalJurisdictionRule).where(
                    IPLegalJurisdictionRule.jurisdiction == jurisdiction
                )
            )
        ).scalars().all()
        return [_to_dict(row) for row in rows]

    async def put_official_source(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalOfficialSource, data)
    async def list_official_sources(self) -> List[Dict[str, Any]]:
        return await self._list(IPLegalOfficialSource)

    async def put_knowledge_verification(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalKnowledgeVerification, data)
    async def get_knowledge_verification(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalKnowledgeVerification, record_id)

    async def put_obligation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalObligation, data)
    async def list_obligations(self) -> List[Dict[str, Any]]:
        return await self._list(IPLegalObligation)

    async def put_business_review(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalBusinessReview, data)
    async def get_business_review(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalBusinessReview, record_id)

    async def put_ethics_review(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalEthicsReview, data)
    async def get_ethics_review(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalEthicsReview, record_id)

    async def put_dispute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalDisputeCase, data)
    async def get_dispute(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalDisputeCase, record_id)
    async def list_disputes(self) -> List[Dict[str, Any]]:
        return await self._list(IPLegalDisputeCase)

    async def put_incident(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalIncidentCase, data)
    async def get_incident(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalIncidentCase, record_id)

    async def put_legal_hold(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalLegalHold, data)
    async def get_legal_hold(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalLegalHold, record_id)

    async def put_rights_contact(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalRightsContact, data)
    async def list_rights_contacts(self) -> List[Dict[str, Any]]:
        return await self._list(IPLegalRightsContact)

    async def put_deadline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalComplianceDeadline, data)
    async def list_deadlines(self) -> List[Dict[str, Any]]:
        return await self._list(IPLegalComplianceDeadline)

    async def put_evidence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalEvidenceRecord, data)
    async def get_evidence(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalEvidenceRecord, record_id)
    async def list_evidence(self) -> List[Dict[str, Any]]:
        return await self._list(IPLegalEvidenceRecord)

    async def put_continuity(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalContinuityRecord, data)
    async def get_continuity(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalContinuityRecord, record_id)

    async def put_policy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalPolicy, data)
    async def get_policy(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self._get(IPLegalPolicy, record_id)
    async def active_policy(self) -> Optional[Dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(IPLegalPolicy).where(IPLegalPolicy.status == "active")
            )
        ).scalars().all()
        return _to_dict(rows[-1]) if rows else None

    async def last_sequence(self) -> int:
        row = (
            await self.db.execute(
                select(IPLegalAuditEvent.sequence).order_by(IPLegalAuditEvent.sequence.desc()).limit(1)
            )
        ).scalar_one_or_none()
        return int(row or 0)

    async def last_hash(self) -> str:
        row = (
            await self.db.execute(
                select(IPLegalAuditEvent.event_hash)
                .order_by(IPLegalAuditEvent.sequence.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return str(row) if row else "0" * 64

    async def append_audit(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await self._put(IPLegalAuditEvent, data)
    async def list_audit(self, limit: int = 100) -> List[Dict[str, Any]]:
        rows = (
            await self.db.execute(
                select(IPLegalAuditEvent)
                .order_by(IPLegalAuditEvent.sequence.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [_to_dict(row) for row in rows]
