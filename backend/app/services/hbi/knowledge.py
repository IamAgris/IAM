"""Document 26 (OD-45): governed behavioural knowledge store (Phase 1).

Epistemic discipline is enforced at write time:
- observation requires evidence;
- interpretation requires at least one alternative;
- hypothesis requires a falsifier.
"""

import uuid
from typing import Any, Dict, List, Optional

from app.services.hbi.evidence import verify_claim
from app.services.hbi.schemas import KnowledgeRecordInput


def _dump(model: Any) -> Dict[str, Any]:
    """Pydantic v1/v2 compatible model serialisation."""
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


class KnowledgeStore:
    def __init__(self, db_session: Optional[Any] = None):
        self.db = db_session
        self._records: Dict[str, Dict[str, Any]] = {}
        self.quarantine: List[Dict[str, Any]] = []
        self.hydrated = False

    @staticmethod
    def _row_to_dict(row: Any) -> Dict[str, Any]:
        """Convert a persisted HBIKnowledgeRecord row into an epistemic dict."""
        return {
            "record_ref": row.record_ref,
            "claim": row.claim,
            "epistemic_type": row.epistemic_type,
            "evidence_class": row.evidence_class,
            "scope": row.scope,
            "tier": row.tier,
            "population": row.population,
            "context_dimensions": row.context_dimensions or {},
            "evidence": row.evidence or [],
            "confidence": float(row.confidence or 0.0),
            "uncertainty": row.uncertainty or {},
            "alternatives": row.alternatives or [],
            "falsifier": row.falsifier,
            "causal_status": row.causal_status,
            "module_ids": row.module_ids or [],
            "version": row.version or 1,
            "caveat": "Graded epistemic object; not a claim about a person's private psychological state.",
        }

    async def hydrate(self) -> int:
        """Load persisted records into the in-memory cache (DB-backed retrieval)."""
        if self.db is None or self.hydrated:
            return len(self._records)
        from sqlalchemy import select
        from app.models.hbi import HBIKnowledgeRecord
        rows = (await self.db.execute(select(HBIKnowledgeRecord))).scalars().all()
        for row in rows:
            self._records[row.record_ref] = self._row_to_dict(row)
        self.hydrated = True
        return len(self._records)

    def _model_from_dict(self, record: Dict[str, Any]):
        from app.models.hbi import HBIKnowledgeRecord
        return HBIKnowledgeRecord(
            record_ref=record["record_ref"],
            claim=record["claim"],
            epistemic_type=record["epistemic_type"],
            evidence_class=record["evidence_class"],
            scope=record["scope"],
            tier=record["tier"],
            population=record.get("population"),
            context_dimensions=record.get("context_dimensions", {}),
            evidence=record.get("evidence", []),
            confidence=record["confidence"],
            uncertainty=record.get("uncertainty", {}),
            alternatives=record.get("alternatives", []),
            falsifier=record.get("falsifier"),
            causal_status=record.get("causal_status", "correlational"),
            module_ids=record.get("module_ids", []),
            version=record.get("version", 1),
        )

    async def add(self, payload: KnowledgeRecordInput) -> Dict[str, Any]:
        evidence = [_dump(item) for item in payload.evidence]
        verified = verify_claim(evidence)

        if payload.epistemic_type == "observation" and not evidence:
            raise ValueError("observation_requires_evidence")
        if payload.epistemic_type == "interpretation" and not payload.alternatives:
            raise ValueError("interpretation_requires_alternative")
        if payload.epistemic_type == "hypothesis" and not payload.falsifier:
            raise ValueError("hypothesis_requires_falsifier")
        if payload.scope == "individual" and payload.tier != "T3":
            raise ValueError("individual_scope_requires_T3")
        if payload.scope == "aggregate" and payload.tier == "T3":
            raise ValueError("T3_reserved_for_individual_scope")
        allowed_provenance = {
            "licensed_corpus", "direct_observation", "illustrative_fixture",
            "derived", "synthetic",
        }
        if payload.provenance_kind not in allowed_provenance:
            raise ValueError("invalid_provenance_kind")

        record = {
            "record_ref": "hbi_" + uuid.uuid4().hex,
            "claim": payload.claim,
            "epistemic_type": payload.epistemic_type.value,
            "evidence_class": (payload.evidence_class.value if payload.evidence_class else verified["evidence_class"]),
            "scope": payload.scope.value,
            "tier": payload.tier.value,
            "population": payload.population,
            "context_dimensions": dict(payload.context_dimensions),
            "evidence": evidence,
            "confidence": payload.confidence if payload.evidence_class else verified["confidence"],
            "uncertainty": _dump(payload.uncertainty),
            "alternatives": list(payload.alternatives),
            "falsifier": payload.falsifier,
            "causal_status": payload.causal_status.value,
            "module_ids": list(payload.module_ids),
            "provenance_kind": payload.provenance_kind,
            "version": 1,
            "status": "active",
            "superseded_by": None,
            "supersedes": None,
            "verification": {
                k: v for k, v in verified.items() if k != "source_ratings"
            },
            "caveat": "Graded epistemic object; not a claim about a person's private psychological state.",
        }
        self._records[record["record_ref"]] = record
        if self.db is not None:
            self.db.add(self._model_from_dict(record))
            await self.db.flush()
        return record

    def get(self, record_ref: str) -> Optional[Dict[str, Any]]:
        return self._records.get(record_ref)

    def all(self) -> List[Dict[str, Any]]:
        return list(self._records.values())

    def search(self, *, scope: Optional[str] = None, tier: Optional[str] = None,
               epistemic_type: Optional[str] = None, evidence_class: Optional[str] = None,
               keyword: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        results = []
        for record in self._records.values():
            if scope and record["scope"] != scope:
                continue
            if tier and record["tier"] != tier:
                continue
            if epistemic_type and record["epistemic_type"] != epistemic_type:
                continue
            if evidence_class and record["evidence_class"] != evidence_class:
                continue
            if keyword and keyword.lower() not in record["claim"].lower():
                continue
            results.append(record)
        return results[:limit]

    def supersede(self, old_ref: str, new_ref: str, rationale: str) -> Dict[str, Any]:
        """A7: mark an old record superseded without deleting it."""
        old = self._records.get(old_ref)
        new = self._records.get(new_ref)
        if old is None or new is None:
            raise ValueError("unknown_record_reference")
        old["status"] = "superseded"
        old["superseded_by"] = new_ref
        old["supersession_rationale"] = rationale
        new["supersedes"] = old_ref
        new["version"] = old.get("version", 1) + 1
        return {"old_ref": old_ref, "new_ref": new_ref, "version": new["version"]}

    def deprecate(self, record_ref: str, reason: str) -> Dict[str, Any]:
        record = self._records.get(record_ref)
        if record is None:
            raise ValueError("unknown_record_reference")
        record["status"] = "deprecated"
        record["deprecation_reason"] = reason
        return {"record_ref": record_ref, "status": "deprecated", "reason": reason}

    def lineage(self, record_ref: str) -> List[Dict[str, Any]]:
        """Return the revision chain in order, oldest first."""
        chain = []
        current = self._records.get(record_ref)
        while current is not None:
            chain.append({
                "record_ref": current["record_ref"],
                "version": current.get("version", 1),
                "status": current.get("status", "active"),
                "claim": current["claim"],
            })
            previous = current.get("supersedes")
            current = self._records.get(previous) if previous else None
        return list(reversed(chain))

    def claims(self, limit: int = 100) -> List[Dict[str, Any]]:
        return [
            {"record_id": r["record_ref"], "claim": r["claim"], "evidence_class": r["evidence_class"]}
            for r in list(self._records.values())[:limit]
        ]
