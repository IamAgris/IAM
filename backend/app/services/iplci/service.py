"""IPLCI Phase 1 service: rights assessment, gateway, provenance and audit.

The service owns the write path. Every mutation produces a hash-chained audit
event. Permissions are tri-state and fail closed: UNKNOWN never becomes
APPROVED, and a missing or unavailable store yields a BLOCK with
``IPLCI_POLICY_UNAVAILABLE``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

from app.services.iplci import (
    business, collection, continuity, core, disputes, ethics, ip_rights,
    jurisdiction, monitoring, policy, privacy, software, training,
)
from app.services.iplci.store import MemoryStore, SQLStore, Store


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class IPLCIService:
    def __init__(self, store: Optional[Store] = None, db: Any = None):
        if store is None:
            store = SQLStore(db) if db is not None else MemoryStore()
        self.store = store

    def status(self) -> Dict[str, Any]:
        return {
            "phase": 6,
            "implemented_phases": [1, 2, 3, 4, 5, 6],
            "policy_version": core.POLICY_VERSION,
            "risk_policy_version": "2.0",
            "capability_areas": 20,
            "engines": 7,
            "rights": list(core.RIGHTS),
            "decision_classes": list(core.DECISION_CLASSES),
            "default_posture": "fail_closed",
            "scope": (
                "copyright, licence, ownership and provenance checks; "
                "trademark, patent, design-right and software-IP screening; "
                "collection legality, privacy and AI-training governance; "
                "jurisdiction resolution, official-source verification, "
                "business compliance and research ethics; "
                "disputes, incident response, legal holds and continuity; "
                "signed policies, mandatory gateway and integration seams"
            ),
        }

    async def _audit(
        self,
        event_type: str,
        actor: str,
        resource_id: Any,
        decision: Optional[str],
        details: Mapping[str, Any],
    ) -> str:
        previous = await self.store.last_hash()
        event_id = str(uuid.uuid4())
        record: Dict[str, Any] = {
            "id": event_id,
            "sequence": await self.store.last_sequence() + 1,
            "event_type": event_type,
            "actor": actor,
            "resource_id": str(resource_id) if resource_id else None,
            "decision": decision,
            "policy_version": core.POLICY_VERSION,
            "ruleset_version": core.POLICY_VERSION,
            "previous_hash": previous,
            "details": dict(details),
            "created_at": _now_iso(),
        }
        record["event_hash"] = core.audit_hash(previous, record)
        await self.store.append_audit(record)
        return event_id

    async def register_source(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        uri = str(payload.get("uri") or "").strip()
        if not uri:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "uri is required")
        rights_status = payload.get("rights_status") or "UNKNOWN_OWNERSHIP"
        source_class = payload.get("source_class") or "UNVERIFIED"
        if rights_status not in core.RIGHTS_STATUSES:
            raise core.IPLCIError("IPLCI_INVALID_STATUS", "invalid rights_status")
        if source_class not in core.SOURCE_CLASSES:
            raise core.IPLCIError("IPLCI_INVALID_STATUS", "invalid source_class")

        known = {
            "uri", "title", "description", "owner_id", "author", "publisher",
            "acquisition_method", "collection_method", "collected_at",
            "rights_status", "source_class", "jurisdiction", "permission_evidence",
            "licence_id", "expiry_date", "revocation_conditions", "territory",
            "personal_data_present", "privacy_lawful_basis", "attribution_required",
            "licence_flags",
        }
        # Callers may pin a deterministic id (e.g. the legal gateway derives
        # one from the action URI). Honour it so later gate checks can find it.
        supplied_id = str(payload.get("id") or "").strip()
        record: Dict[str, Any] = {
            "id": supplied_id or str(uuid.uuid4()),
            "uri": uri,
            "current_permission_state": "NOT_VALIDATED",
            "permission_withdrawn": False,
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
            "payload": {key: value for key, value in payload.items() if key not in known},
        }
        for key in known:
            if key in payload:
                record[key] = payload[key]
        await self.store.put_source(record)
        await self._audit("source_registered", actor, record["id"], "QUARANTINED", {
            "rights_status": rights_status,
            "source_class": source_class,
            "note": "new sources start unvalidated; unknown rights are not approval",
        })
        await self.store.commit()
        return record

    async def set_permission(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        source_id = str(payload.get("source_id") or "")
        if not await self.store.get_source(source_id):
            raise core.IPLCIError("IPLCI_NOT_FOUND", "source not found")
        right = str(payload.get("right") or "")
        if right not in core.RIGHTS:
            raise core.IPLCIError("IPLCI_INVALID_RIGHT", "invalid right")
        state = str(payload.get("state") or core.UNKNOWN)
        if state not in (core.PERMITTED, core.PROHIBITED, core.UNKNOWN):
            raise core.IPLCIError("IPLCI_INVALID_STATE", "invalid permission state")
        record = {
            "id": str(uuid.uuid4()),
            "source_id": source_id,
            "right": right,
            "state": state,
            "basis": payload.get("basis"),
            "conditions": list(payload.get("conditions") or []),
            "evidence_ref": payload.get("evidence_ref"),
            "assessed_by": actor,
            "assessed_at": _now_iso(),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_permission(record)
        await self._audit("permission_recorded", actor, source_id, state, {
            "right": right, "basis": record["basis"],
        })
        await self.store.commit()
        return record

    async def revoke_permission(self, source_id: str, actor: str = "sdk", reason: str = "") -> Dict[str, Any]:
        source = await self.store.get_source(source_id)
        if not source:
            raise core.IPLCIError("IPLCI_NOT_FOUND", "source not found")
        source["permission_withdrawn"] = True
        source["current_permission_state"] = "REVOKED"
        source["updated_at"] = _now_iso()
        source.setdefault("payload", {})["revocation_reason"] = reason
        await self.store.put_source(source)
        await self._audit("permission_revoked", actor, source_id, "REVOKED", {"reason": reason})
        await self.store.commit()
        return source

    async def _run_assessment(
        self,
        payload: Mapping[str, Any],
        actor: str,
        *,
        gateway: bool,
    ) -> Dict[str, Any]:
        operation = str(payload.get("operation") or "")
        source_id = payload.get("source_id")
        source = await self.store.get_source(str(source_id)) if source_id else None
        permissions = await self.store.list_permissions(str(source_id)) if source_id else []
        if gateway:
            result = core.gate_check(
                source, permissions, operation=operation,
                jurisdiction=payload.get("jurisdiction"),
            )
        else:
            result = core.assess(
                source, permissions, operation=operation,
                jurisdiction=payload.get("jurisdiction"),
            )
        audit_id = await self._audit(
            "gateway_check" if gateway else "rights_assessment",
            actor,
            str(source_id) if source_id else None,
            result.get("decision"),
            {
                "operation": operation,
                "decision_class": result.get("decision_class"),
                "rules_applied": result.get("rules_applied", []),
                "reason": result.get("reason"),
                "error_code": result.get("error_code"),
            },
        )
        record = {
            "id": str(uuid.uuid4()),
            "source_id": str(source_id) if source_id else None,
            "operation": operation,
            "agent_id": str(payload.get("agent_id") or actor),
            "decision": result["decision"],
            "decision_class": result["decision_class"],
            "jurisdiction": payload.get("jurisdiction"),
            "reason": result.get("reason"),
            "rules_applied": result.get("rules_applied", []),
            "evidence_refs": result.get("evidence_refs", []),
            "rights_evaluated": result.get("rights_evaluated", {}),
            "conditions": result.get("conditions", []),
            "policy_version": result.get("policy_version", core.POLICY_VERSION),
            "payload": {
                key: value for key, value in result.items()
                if key not in ("decision", "decision_class", "reason", "rules_applied",
                               "evidence_refs", "rights_evaluated", "conditions",
                               "policy_version", "right", "audit_event_id")
            },
            "created_at": _now_iso(),
        }
        await self.store.put_assessment(record)
        result["id"] = record["id"]
        result["audit_event_id"] = audit_id
        await self.store.commit()
        return result

    async def assess(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        return await self._run_assessment(payload, actor, gateway=False)

    async def gate_check(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        """Mandatory pre-execution check. Fails closed on any store error."""
        try:
            return await self._run_assessment(payload, actor, gateway=True)
        except Exception as exc:  # pragma: no cover - defensive boundary
            return {
                "decision": "BLOCKED",
                "decision_class": "UNKNOWN",
                "error_code": "IPLCI_POLICY_UNAVAILABLE",
                "reason": f"rights assessment unavailable: {type(exc).__name__}",
                "policy_version": core.POLICY_VERSION,
                "audit_event_id": None,
            }

    async def _record_risk(
        self,
        result: Mapping[str, Any],
        subject: str,
        jurisdiction: Optional[str],
        actor: str,
        evidence: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        risk_level = str(result.get("risk") or "UNKNOWN")
        decision = str(result.get("decision") or (
            "APPROVED" if result.get("eligible") is True else
            "QUARANTINED" if risk_level == "UNKNOWN" else
            "BLOCKED" if risk_level in ("HIGH", "CRITICAL") else
            "CONDITIONAL"
        ))
        record = {
            "id": str(uuid.uuid4()),
            "domain": result.get("domain") or "unknown",
            "subject": subject,
            "jurisdiction": jurisdiction,
            "risk": risk_level,
            "decision": decision,
            "outcome": result.get("outcome") or "review_required",
            "reasons": list(result.get("reasons") or []),
            "evidence": list(evidence or []),
            "professional_review_required": bool(result.get("professional_review_required")),
            "policy_version": result.get("policy_version") or "2.0",
            "payload": {
                key: value for key, value in result.items()
                if key not in ("domain", "subject", "risk", "outcome", "reasons",
                               "professional_review_required", "policy_version")
            },
            "created_at": _now_iso(),
        }
        await self.store.put_risk(record)
        await self._audit("risk_decision", actor, record["id"], record["risk"], {  # type: ignore[arg-type]
            "domain": record["domain"],
            "subject": subject,
            "outcome": record["outcome"],
            "professional_review_required": record["professional_review_required"],
        })
        await self.store.commit()
        return {**result, "decision": decision, "id": record["id"]}

    async def risk_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        return await self.store.get_risk(decision_id)

    async def register_trademark(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        mark_text = str(payload.get("mark_text") or "").strip()
        owner = str(payload.get("owner") or "").strip()
        if not mark_text or not owner:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "mark_text and owner are required")
        status = payload.get("status") or "registered"
        if status not in ip_rights.TRADEMARK_STATUSES:
            raise core.IPLCIError("IPLCI_INVALID_STATUS", "invalid trademark status")
        known = {
            "mark_text", "owner", "jurisdiction", "classes", "status",
            "registration_number", "goods_services", "logo_hash", "territory",
            "filed_at", "registered_at", "expires_at",
        }
        record = {
            "id": str(uuid.uuid4()),
            "mark_text": mark_text,
            "owner": owner,
            "status": status,
            "classes": list(payload.get("classes") or []),
            "territory": payload.get("territory"),
            "payload": {key: value for key, value in payload.items() if key not in known},
            "created_at": _now_iso(),
        }
        for key in known - {"mark_text", "owner", "status", "classes", "territory"}:
            if key in payload:
                record[key] = payload[key]
        await self.store.put_trademark(record)
        await self._audit("trademark_registered", actor, record["id"], "QUARANTINED", {
            "mark_text": mark_text, "status": status,
        })
        await self.store.commit()
        return record

    async def check_trademark(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        proposed = str(payload.get("proposed") or "")
        marks = await self.store.list_trademarks()
        result = ip_rights.check_trademark(
            proposed, marks,
            jurisdiction=payload.get("jurisdiction"),
            classes=list(payload.get("classes") or []),
            use_context=payload.get("use_context") or "brand_use",
            now=payload.get("now"),
        )
        return await self._record_risk(
            result, proposed, payload.get("jurisdiction"), actor,
            [str(conflict.get("mark_id") or "") for conflict in result.get("conflicts", [])],
        )

    async def register_patent(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        number = str(payload.get("publication_number") or "").strip()
        title = str(payload.get("title") or "").strip()
        if not number or not title:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "publication_number and title are required")
        status = payload.get("status") or "pending"
        if status not in ip_rights.PATENT_STATUSES:
            raise core.IPLCIError("IPLCI_INVALID_STATUS", "invalid patent status")
        known = {
            "publication_number", "title", "owner", "jurisdiction", "status",
            "claims", "filed_at", "priority_at", "expires_at", "family_id",
        }
        record = {
            "id": str(uuid.uuid4()),
            "publication_number": number,
            "title": title,
            "status": status,
            "jurisdiction": list(payload.get("jurisdiction") or []),
            "claims": list(payload.get("claims") or []),
            "payload": {key: value for key, value in payload.items() if key not in known},
            "created_at": _now_iso(),
        }
        for key in known - {"publication_number", "title", "status", "jurisdiction", "claims"}:
            if key in payload:
                record[key] = payload[key]
        await self.store.put_patent(record)
        await self._audit("patent_registered", actor, record["id"], "QUARANTINED", {
            "publication_number": number, "status": status,
        })
        await self.store.commit()
        return record

    async def check_patent(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        activity = str(payload.get("activity") or "")
        implementation = str(payload.get("implementation") or "")
        patents = await self.store.list_patents()
        result = ip_rights.check_patent_fto(
            activity, implementation, list(payload.get("features") or []), patents,
            jurisdiction=payload.get("jurisdiction"), now=payload.get("now"),
        )
        return await self._record_risk(
            result, implementation or activity, payload.get("jurisdiction"), actor,
            [str(item.get("patent_id") or "") for item in result.get("overlaps", [])],
        )

    async def register_design(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        subject = str(payload.get("subject") or "").strip()
        right_type = str(payload.get("right_type") or "")
        if not subject:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "subject is required")
        if right_type not in ip_rights.DESIGN_RIGHT_TYPES:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "invalid right_type")
        known = {
            "right_type", "subject", "owner", "jurisdiction",
            "registration_number", "status", "expires_at",
        }
        record = {
            "id": str(uuid.uuid4()),
            "subject": subject,
            "right_type": right_type,
            "status": payload.get("status") or "unregistered",
            "payload": {key: value for key, value in payload.items() if key not in known},
            "created_at": _now_iso(),
        }
        for key in known - {"subject", "right_type", "status"}:
            if key in payload:
                record[key] = payload[key]
        await self.store.put_design(record)
        await self._audit("design_right_registered", actor, record["id"], "QUARANTINED", {
            "subject": subject, "right_type": right_type,
        })
        await self.store.commit()
        return record

    async def check_design(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        subject = str(payload.get("subject") or "")
        rights = await self.store.list_designs()
        result = ip_rights.check_design(
            subject, rights, right_type=payload.get("right_type"),
            jurisdiction=payload.get("jurisdiction"), now=payload.get("now"),
        )
        return await self._record_risk(
            result, subject, payload.get("jurisdiction"), actor,
            [str(item.get("right_id") or "") for item in result.get("matches", [])],
        )

    async def record_dependency(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        project_id = str(payload.get("project_id") or "").strip()
        name = str(payload.get("name") or "").strip()
        if not project_id or not name:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "project_id and name are required")
        origin = payload.get("origin") or "third_party"
        if origin not in software.SOURCE_ORIGINS:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "invalid origin")
        record = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "name": name,
            "version": payload.get("version"),
            "licence_id": payload.get("licence_id"),
            "source_url": payload.get("source_url"),
            "origin": origin,
            "vulnerability_status": payload.get("vulnerability_status"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_dependency(record)
        await self._audit("dependency_recorded", actor, record["id"], "QUARANTINED", {
            "project_id": project_id, "name": name, "licence_id": record["licence_id"],
        })
        await self.store.commit()
        return record

    async def check_dependency(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = software.check_dependency(
            payload.get("licence_id"),
            distribution=payload.get("distribution") or "internal",
            project_licence=payload.get("project_licence"),
            modification=bool(payload.get("modification")),
            network_service=bool(payload.get("network_service")),
            vulnerability_status=payload.get("vulnerability_status"),
        )
        return await self._record_risk(
            result, str(payload.get("licence_id") or "unknown"), None, actor,
            [str(payload.get("dependency_id") or "")],
        )

    async def check_source_origin(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = software.check_source_origin(
            str(payload.get("origin") or ""),
            third_party_licence=payload.get("third_party_licence"),
        )
        return await self._record_risk(result, str(payload.get("origin") or ""), None, actor)

    async def record_sbom(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        project_id = str(payload.get("project_id") or "").strip()
        if not project_id:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "project_id is required")
        components = list(payload.get("components") or [])
        record = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "components": components,
            "generated_at": payload.get("generated_at") or _now_iso(),
            "payload": {"summary": software.summarise_sbom(components)},
            "created_at": _now_iso(),
        }
        await self.store.put_sbom(record)
        await self._audit("sbom_recorded", actor, record["id"], "APPROVED", {
            "project_id": project_id, "components": len(components),
        })
        await self.store.commit()
        return record

    async def sbom_report(self, sbom_id: str) -> Dict[str, Any]:
        sbom = await self.store.get_sbom(sbom_id)
        if not sbom:
            raise core.IPLCIError("IPLCI_NOT_FOUND", "sbom not found")
        return software.summarise_sbom(sbom.get("components") or [])

    # --- Phase 3: collection legality, privacy and training governance ---

    async def assess_collection(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        uri = str(payload.get("source_uri") or "").strip()
        if not uri:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "source_uri is required")
        flag_keys = (
            "terms_of_service_restricts_collection", "robots_txt",
            "api_terms_restrict_use", "paywall", "login_required",
            "access_control", "scraping_restricted", "rate_limited",
            "rate_limits_respected", "personal_data", "commercial_reuse_restricted",
            "database_rights", "automated_collection_restricted",
            "permission_evidence", "bypassed_paywall", "bypassed_authentication",
            "circumvented_tpm", "bypassed_access_control",
        )
        flags = {key: payload[key] for key in flag_keys if key in payload}
        result = collection.assess_collection(
            flags, intended_use=payload.get("intended_use") or "research",
        )
        record = {
            "id": str(uuid.uuid4()),
            "source_uri": uri,
            "intended_use": payload.get("intended_use") or "research",
            "risk": result["risk"],
            "outcome": result["outcome"],
            "blocked": result["blocked"],
            "flags": flags,
            "conditions": result["conditions"],
            "reasons": result["reasons"],
            "policy_version": result["policy_version"],
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_collection_check(record)
        await self._audit("collection_assessed", actor, record["id"], result["risk"], {
            "source_uri": uri, "blocked": result["blocked"],
        })
        await self.store.commit()
        return {**result, "id": record["id"]}

    async def collection_check(self, check_id: str) -> Optional[Dict[str, Any]]:
        return await self.store.get_collection_check(check_id)

    async def record_privacy(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        jurisdiction = str(payload.get("jurisdiction") or "ZA")
        record = {
            "id": str(uuid.uuid4()),
            "source_id": payload.get("source_id"),
            "jurisdiction": jurisdiction,
            "personal_data_present": bool(payload.get("personal_data_present")),
            "data_categories": list(payload.get("data_categories") or []),
            "lawful_basis": payload.get("lawful_basis"),
            "explicit_consent": bool(payload.get("explicit_consent")),
            "dpia_completed": bool(payload.get("dpia_completed")),
            "minimisation_applied": bool(payload.get("minimisation_applied")),
            "retention_period": payload.get("retention_period"),
            "deletion_supported": bool(payload.get("deletion_supported")),
            "deletion_requested": bool(payload.get("deletion_requested")),
            "deletion_completed": bool(payload.get("deletion_completed")),
            "dsar_requested": bool(payload.get("dsar_requested")),
            "dsar_completed": bool(payload.get("dsar_completed")),
            "international_transfer": bool(payload.get("international_transfer")),
            "transfer_mechanism": payload.get("transfer_mechanism"),
            "disclosure_permitted": bool(payload.get("disclosure_permitted")),
            "verification_status": "requires_verification",
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        result = privacy.assess_privacy(
            record,
            jurisdiction=jurisdiction,
            purpose=payload.get("purpose") or "research",
            operation=payload.get("operation") or "analyse",
        )
        record["risk"] = result["risk"]
        record["outcome"] = result["outcome"]
        await self.store.put_privacy(record)
        decision = await self._record_risk(
            result, str(payload.get("source_id") or "privacy_record"), jurisdiction, actor,
        )
        await self.store.commit()
        return {**decision, "privacy_id": record["id"]}

    async def assess_privacy(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = privacy.assess_privacy(
            payload,
            jurisdiction=str(payload.get("jurisdiction") or "ZA"),
            purpose=payload.get("purpose") or "research",
            operation=payload.get("operation") or "analyse",
        )
        return await self._record_risk(
            result, str(payload.get("subject") or "privacy_record"),
            payload.get("jurisdiction"), actor,
        )

    async def privacy_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self.store.get_privacy(record_id)

    async def record_training_approval(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        approver = str(payload.get("approver") or "").strip()
        reviewer = str(payload.get("ingestion_reviewer") or "").strip()
        if not approver or not reviewer:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "approver and ingestion_reviewer are required")
        decision = payload.get("decision") or "approved"
        if decision not in ("pending", "approved", "rejected", "revoked"):
            raise core.IPLCIError("IPLCI_INVALID_STATUS", "invalid approval decision")
        if decision == "approved" and approver == reviewer:
            raise core.IPLCIError(
                "IPLCI_INDEPENDENT_APPROVAL_REQUIRED",
                "training approver must differ from the ingestion reviewer",
            )
        if decision == "approved" and not str(payload.get("basis") or "").strip():
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "approval basis is required")
        record = {
            "id": str(uuid.uuid4()),
            "source_id": payload.get("source_id"),
            "dataset_id": payload.get("dataset_id"),
            "requester": payload.get("requester") or actor,
            "approver": approver,
            "ingestion_reviewer": reviewer,
            "decision": decision,
            "basis": payload.get("basis"),
            "purpose": payload.get("purpose"),
            "expires_at": payload.get("expires_at"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_training_approval(record)
        await self._audit("training_approval_recorded", actor, record["id"], decision, {
            "approver": approver, "ingestion_reviewer": reviewer,
        })
        await self.store.commit()
        return record

    async def training_gate(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        """Mandatory training gate: rights + provenance + independent approval."""
        source_id = str(payload.get("source_id") or "")
        dataset_id = str(payload.get("dataset_id") or "")
        if not source_id or not dataset_id:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "source_id and dataset_id are required")
        source = await self.store.get_source(source_id)
        permissions = await self.store.list_permissions(source_id)
        dataset = await self.store.get_dataset(dataset_id) or {}
        approval = await self.store.get_training_approval(str(payload.get("approval_id") or ""))
        if not approval and dataset_id:
            for candidate in (dataset.get("approval_ids") or []):
                found = await self.store.get_training_approval(str(candidate))
                if found:
                    approval = found
                    break
        flags = dict(dataset.get("payload") or {})
        for key in (
            "lawfully_obtained", "provenance_recorded", "privacy_lawful_basis",
            "personal_data_present", "approval_expiry",
        ):
            if key in dataset and dataset[key] is not None:
                flags[key] = dataset[key]
        result = training.assess_training(
            source, permissions, dataset=flags, approval=approval,
            jurisdiction=payload.get("jurisdiction"), now=payload.get("now"),
        )
        return await self._record_risk(
            result, dataset_id, payload.get("jurisdiction"), actor,
            [source_id, str(payload.get("approval_id") or "")],
        )

    async def assess_foundation_model(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        model_id = str(payload.get("model_id") or "").strip()
        if not model_id:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "model_id is required")
        result = training.assess_foundation_model(
            model_id, payload.get("licence_id"),
            commercial=bool(payload.get("commercial")),
            modify=bool(payload.get("modify")),
            redistribute=bool(payload.get("redistribute")),
        )
        return await self._record_risk(result, model_id, None, actor)

    async def assess_provider(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = training.assess_provider(payload)
        return await self._record_risk(result, str(result["subject"]), None, actor)

    async def _dataset_states(self, dataset_ids: Iterable[str]) -> Dict[str, str]:
        states: Dict[str, str] = {}
        for dataset_id in dataset_ids:
            dataset = await self.store.get_dataset(str(dataset_id))
            state = "NOT_VALIDATED"
            if dataset:
                status = str(dataset.get("approval_status") or "pending").upper()
                state = "REVOKED" if status == "REVOKED" else (
                    "APPROVED" if status == "APPROVED" else "NOT_VALIDATED"
                )
                for source_id in dataset.get("source_ids") or []:
                    source = await self.store.get_source(str(source_id))
                    if source and str(source.get("current_permission_state")).upper() in (
                        "REVOKED", "EXPIRED", "BLOCKED", "QUARANTINED"
                    ):
                        state = "REVOKED"
            states[str(dataset_id)] = state
        return states

    async def register_lineage(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        model_id = str(payload.get("model_id") or "").strip()
        base_model = str(payload.get("base_model") or "").strip()
        if not model_id or not base_model:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "model_id and base_model are required")
        dataset_ids = list(payload.get("dataset_ids") or [])
        states = await self._dataset_states(dataset_ids)
        check = training.check_lineage({"model_id": model_id}, dataset_ids, states)
        record = {
            "id": str(uuid.uuid4()),
            "model_id": model_id,
            "base_model": base_model,
            "base_model_version": payload.get("base_model_version"),
            "base_model_licence": payload.get("base_model_licence"),
            "dataset_ids": dataset_ids,
            "approval_ids": list(payload.get("approval_ids") or []),
            "training_date": payload.get("training_date") or _now_iso(),
            "evaluation_ref": payload.get("evaluation_ref"),
            "promotion_status": payload.get("promotion_status") or "candidate",
            "affected_by_revocation": check["affected_dataset_ids"],
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_lineage(record)
        await self._audit("model_lineage_registered", actor, record["id"], check["risk"], {
            "model_id": model_id, "affected_dataset_ids": check["affected_dataset_ids"],
        })
        await self.store.commit()
        return record

    async def check_lineage(self, lineage_id: str, actor: str = "sdk") -> Dict[str, Any]:
        record = await self.store.get_lineage(lineage_id)
        if not record:
            raise core.IPLCIError("IPLCI_NOT_FOUND", "lineage not found")
        states = await self._dataset_states(record.get("dataset_ids") or [])
        check = training.check_lineage(record, record.get("dataset_ids") or [], states)
        record["affected_by_revocation"] = check["affected_dataset_ids"]
        await self.store.put_lineage(record)
        await self._audit("lineage_rechecked", actor, lineage_id, check["risk"], {
            "affected_dataset_ids": check["affected_dataset_ids"],
        })
        await self.store.commit()
        return {**check, "lineage_id": lineage_id, "lineage": record}

    # --- Phase 4: jurisdiction, verification, business compliance and ethics ---

    async def resolve_jurisdiction(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = jurisdiction.resolve_jurisdictions(
            origin=payload.get("origin"),
            processing_locations=list(payload.get("processing_locations") or []),
            target_markets=list(payload.get("target_markets") or []),
            establishment=payload.get("establishment"),
        )
        enriched = {
            **result,
            "risk": "MODERATE" if result["escalation_required"] else "LOW",
            "outcome": "escalate" if result["escalation_required"] else "resolved",
        }
        return await self._record_risk(
            enriched, str(payload.get("origin") or "jurisdiction"), None, actor,
        )

    async def register_jurisdiction_rule(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        required = ("jurisdiction", "domain", "provision")
        if any(not payload.get(field) for field in required):
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "jurisdiction, domain and provision are required")
        record = {
            "id": str(uuid.uuid4()),
            "jurisdiction": str(payload["jurisdiction"]).upper()[:2],
            "domain": payload["domain"],
            "provision": payload["provision"],
            "source_ref": payload.get("source_ref"),
            "verification_status": "requires_verification",
            "effective_from": payload.get("effective_from"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_jurisdiction_rule(record)
        await self._audit("jurisdiction_rule_registered", actor, record["id"], "QUARANTINED", {
            "jurisdiction": record["jurisdiction"], "provision": record["provision"],
        })
        await self.store.commit()
        return record

    async def applicable_laws(self, jurisdictions: Iterable[str], domain: str) -> Dict[str, Any]:
        return {
            "domain": domain,
            "provisions": jurisdiction.applicable_law(jurisdictions, domain),
            "legal_context_status": "requires_verification",
        }

    async def register_official_source(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        required = ("authority", "jurisdiction", "url")
        if any(not payload.get(field) for field in required):
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "authority, jurisdiction and url are required")
        record = {
            "id": str(uuid.uuid4()),
            "authority": payload["authority"],
            "authority_type": payload.get("authority_type") or "regulator",
            "jurisdiction": str(payload["jurisdiction"]).upper()[:2],
            "url": payload["url"],
            "verified_by": payload.get("verified_by"),
            "verified_at": payload.get("verified_at"),
            "last_checked_at": payload.get("last_checked_at") or _now_iso(),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_official_source(record)
        await self._audit("official_source_registered", actor, record["id"], "APPROVED", {
            "authority": record["authority"], "jurisdiction": record["jurisdiction"],
        })
        await self.store.commit()
        return record

    async def verify_legal_source(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = jurisdiction.verify_official_source(payload)
        record = {
            "id": str(uuid.uuid4()),
            "claim": str(payload.get("claim") or payload.get("provision_ref") or "legal claim"),
            "jurisdiction": payload.get("jurisdiction"),
            "source_url": payload.get("url"),
            "provision_ref": payload.get("provision_ref"),
            "document_type": payload.get("document_type") or "guidance",
            "status": result["status"],
            "reviewer": payload.get("verified_by"),
            "reviewed_at": payload.get("verified_at"),
            "checked_at": _now_iso(),
            "reasons": result["problems"] + result["missing_fields"],
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_knowledge_verification(record)
        await self._audit("legal_source_verified", actor, record["id"], result["status"], {
            "authority": result["authority"], "status": result["status"],
            "verified_by": result["verified_by"],
        })
        await self.store.commit()
        return {**result, "verification_id": record["id"]}

    async def knowledge_verification(self, verification_id: str) -> Optional[Dict[str, Any]]:
        return await self.store.get_knowledge_verification(verification_id)

    async def assess_legal_change(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = jurisdiction.assess_legal_change(payload)
        return await self._record_risk(
            result, str(payload.get("title") or result["document_type"]),
            payload.get("jurisdiction"), actor,
        )

    async def assess_business(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = business.assess_business_activity(payload)
        record = {
            "id": str(uuid.uuid4()),
            "activity": str(payload.get("description") or result["action"]),
            "business_domain": result["business_domain"],
            "jurisdiction": payload.get("jurisdiction"),
            "risk": result["risk"],
            "outcome": result["outcome"],
            "obligations": result["obligations"],
            "blockers": result["blockers"],
            "human_approval_required": result["human_approval_required"],
            "approval_reference": payload.get("human_approval_reference"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_business_review(record)
        await self._audit("business_activity_reviewed", actor, record["id"], result["risk"], {
            "business_domain": result["business_domain"],
            "human_approval_required": result["human_approval_required"],
        })
        await self.store.commit()
        return {**result, "review_id": record["id"]}

    async def business_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        return await self.store.get_business_review(review_id)

    async def record_obligation(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        if not payload.get("obligation"):
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "obligation is required")
        record = {
            "id": str(uuid.uuid4()),
            "domain": payload.get("domain") or "contract",
            "jurisdiction": payload.get("jurisdiction"),
            "obligation": payload["obligation"],
            "source_ref": payload.get("source_ref"),
            "responsible_party": payload.get("responsible_party"),
            "due_at": payload.get("due_at"),
            "status": "open",
            "evidence_ref": payload.get("evidence_ref"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_obligation(record)
        await self._audit("obligation_recorded", actor, record["id"], "CONDITIONAL", {
            "domain": record["domain"], "due_at": record["due_at"],
        })
        await self.store.commit()
        return record

    async def obligations(self) -> List[Dict[str, Any]]:
        return await self.store.list_obligations()

    async def _ethics_review(
        self,
        review_type: str,
        subject: str,
        result: Mapping[str, Any],
        jurisdiction: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        record = {
            "id": str(uuid.uuid4()),
            "review_type": review_type,
            "subject": subject,
            "jurisdiction": jurisdiction,
            "risk": result["risk"],
            "outcome": result["outcome"],
            "requirements": list(result.get("requirements") or result.get("conditions") or []),
            "payload": dict(result),
            "created_at": _now_iso(),
        }
        await self.store.put_ethics_review(record)
        await self._audit("ethics_review_recorded", actor, record["id"], result["risk"], {
            "review_type": review_type, "subject": subject,
        })
        await self.store.commit()
        return {**result, "review_id": record["id"]}

    async def assess_research_ethics(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = ethics.assess_research_ethics(payload)
        return await self._ethics_review(
            "research_ethics", str(payload.get("subject") or "research_activity"),
            result, payload.get("jurisdiction"), actor,
        )

    async def assess_identity_use(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = ethics.assess_identity_use(payload)
        return await self._ethics_review(
            "identity", str(payload.get("subject") or "identity_use"),
            result, payload.get("jurisdiction"), actor,
        )

    async def assess_cross_border(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = ethics.assess_cross_border(payload)
        return await self._ethics_review(
            "cross_border", str(payload.get("origin") or "transfer"),
            result, payload.get("origin"), actor,
        )

    async def ethics_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        return await self.store.get_ethics_review(review_id)

    # --- Phase 5: disputes, incidents, holds, monitoring and continuity ---

    async def register_dispute(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        case_type = str(payload.get("case_type") or "")
        verification = disputes.verify_complainant(payload)
        assessment = disputes.assess_dispute(payload, verification)
        record = {
            "id": str(uuid.uuid4()),
            "case_type": case_type,
            "complainant": payload.get("complainant"),
            "claim_ref": payload.get("claim_ref"),
            "authority_verified": verification["verified"],
            "status": "verifying" if not verification["verified"] else "investigating",
            "affected_assets": list(payload.get("affected_assets") or []),
            "affected_datasets": list(payload.get("affected_datasets") or []),
            "affected_models": list(payload.get("affected_models") or []),
            "evidence_refs": list(payload.get("evidence_refs") or []),
            "deadlines": list(payload.get("deadlines") or []),
            "case_history": [{"event": "received", "actor": actor, "at": _now_iso()}],
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        await self.store.put_dispute(record)
        await self._audit("dispute_received", actor, record["id"], assessment["risk"], {
            "case_type": case_type,
            "authority_verified": verification["verified"],
            "accepted_allegation": False,
        })
        await self.store.commit()
        return {**assessment, "dispute_id": record["id"], "case": record}

    async def dispute(self, dispute_id: str) -> Optional[Dict[str, Any]]:
        return await self.store.get_dispute(dispute_id)

    async def disputes(self) -> List[Dict[str, Any]]:
        return await self.store.list_disputes()

    async def update_dispute_status(
        self, dispute_id: str, status: str, actor: str = "sdk", note: str = ""
    ) -> Dict[str, Any]:
        if status not in disputes.CASE_STATUSES:
            raise core.IPLCIError("IPLCI_INVALID_STATUS", "invalid dispute status")
        record = await self.store.get_dispute(dispute_id)
        if not record:
            raise core.IPLCIError("IPLCI_NOT_FOUND", "dispute not found")
        record["status"] = status
        record.setdefault("case_history", []).append({
            "event": status, "actor": actor, "at": _now_iso(), "note": note,
        })
        record["updated_at"] = _now_iso()
        await self.store.put_dispute(record)
        await self._audit("dispute_status_changed", actor, dispute_id, status, {"note": note})
        await self.store.commit()
        return record

    async def open_incident(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        incident_type = str(payload.get("incident_type") or "").strip()
        if not incident_type:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "incident_type is required")
        record = {
            "id": str(uuid.uuid4()),
            "incident_type": incident_type,
            "detected_at": payload.get("detected_at") or _now_iso(),
            "stopped_at": payload.get("stopped_at"),
            "affected_sources": list(payload.get("affected_sources") or []),
            "affected_projects": list(payload.get("affected_projects") or []),
            "affected_models": list(payload.get("affected_models") or []),
            "exposure_assessment": payload.get("exposure_assessment"),
            "notification_required": bool(payload.get("notification_required")),
            "notification_decision": payload.get("notification_decision"),
            "disclosure_type": payload.get("disclosure_type"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_incident(record)
        steps = disputes.remediation_steps(payload)
        await self._audit("incident_opened", actor, str(record["id"]), "CRITICAL", {
            "incident_type": incident_type,
            "affected_models": record["affected_models"],
        })
        await self.store.commit()
        return {"incident_id": record["id"], "incident": record, "remediation_steps": steps}

    async def incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        return await self.store.get_incident(incident_id)

    async def place_legal_hold(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        reason = str(payload.get("reason") or "").strip()
        if not reason:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "reason is required")
        record = {
            "id": str(uuid.uuid4()),
            "reason": reason,
            "case_id": payload.get("case_id"),
            "scope": list(payload.get("scope") or []),
            "issued_by": actor,
            "issued_at": _now_iso(),
            "payload": dict(payload.get("payload") or {}),
        }
        await self.store.put_legal_hold(record)
        await self._audit("legal_hold_placed", actor, str(record["id"]), "HIGH", {
            "reason": reason, "scope": record["scope"],
        })
        await self.store.commit()
        return record

    async def release_legal_hold(self, hold_id: str, actor: str = "sdk") -> Dict[str, Any]:
        record = await self.store.get_legal_hold(hold_id)
        if not record:
            raise core.IPLCIError("IPLCI_NOT_FOUND", "legal hold not found")
        record["released_at"] = _now_iso()
        record["released_by"] = actor
        await self.store.put_legal_hold(record)
        await self._audit("legal_hold_released", actor, hold_id, "LOW", {})
        await self.store.commit()
        return record

    async def evidence_guard(self, hold_id: Optional[str] = None) -> Dict[str, Any]:
        hold = await self.store.get_legal_hold(hold_id) if hold_id else None
        if not hold and hold_id:
            raise core.IPLCIError("IPLCI_NOT_FOUND", "legal hold not found")
        return continuity.legal_hold_guard(hold, await self.store.list_evidence())

    async def record_rights_contact(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        request_type = str(payload.get("request_type") or "")
        if request_type not in disputes.REQUEST_TYPES:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "invalid request_type")
        record = {
            "id": str(uuid.uuid4()),
            "party_id": payload.get("party_id"),
            "request_type": request_type,
            "requested_rights": list(payload.get("requested_rights") or []),
            "status": "requested",
            "agreement_ref": payload.get("agreement_ref"),
            "review_date": payload.get("review_date"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_rights_contact(record)
        await self._audit("rights_contact_recorded", actor, str(record["id"]), "CONDITIONAL", {
            "request_type": request_type,
        })
        await self.store.commit()
        return record

    async def rights_contacts(self) -> List[Dict[str, Any]]:
        return await self.store.list_rights_contacts()

    async def record_deadline(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        kind = str(payload.get("deadline_type") or "")
        if kind not in monitoring.DEADLINE_TYPES:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "invalid deadline_type")
        record = {
            "id": str(uuid.uuid4()),
            "deadline_type": kind,
            "source_ref": payload.get("source_ref"),
            "jurisdiction": payload.get("jurisdiction"),
            "due_at": payload.get("due_at"),
            "notify_before": payload.get("notify_before"),
            "status": "open",
            "proof_ref": payload.get("proof_ref"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_deadline(record)
        await self._audit("compliance_deadline_recorded", actor, str(record["id"]), "CONDITIONAL", {
            "deadline_type": kind, "due_at": record["due_at"],
        })
        await self.store.commit()
        return record

    async def compliance_calendar(self, now: Optional[str] = None) -> Dict[str, Any]:
        return monitoring.compliance_calendar(await self.store.list_deadlines(), now=now)

    async def permission_changes(self, now: Optional[str] = None) -> Dict[str, Any]:
        changes = monitoring.detect_permission_changes(await self.store.list_sources(), now=now)
        return {
            "domain": "compliance_monitoring",
            "changes": changes,
            "risk": "CRITICAL" if any(item["risk"] == "CRITICAL" for item in changes) else (
                "HIGH" if changes else "LOW"
            ),
            "reassessment_required": bool(changes),
        }

    async def check_reassessment(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        result = monitoring.reassessment_trigger(payload)
        if result["required"]:
            await self._audit("reassessment_triggered", actor, None, result["risk"], {
                "triggers": result["triggers"],
            })
            await self.store.commit()
        return result

    async def record_evidence(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        record = {
            "id": str(uuid.uuid4()),
            "asset_id": payload.get("asset_id"),
            "case_id": payload.get("case_id"),
            "legal_hold_id": payload.get("legal_hold_id"),
            "source_url": payload.get("source_url"),
            "document_ref": payload.get("document_ref"),
            "legal_provision_ref": payload.get("legal_provision_ref"),
            "licence_version": payload.get("licence_version"),
            "captured_at": payload.get("captured_at") or _now_iso(),
            "jurisdiction": payload.get("jurisdiction"),
            "content_hash": payload.get("content_hash"),
            "retention_until": payload.get("retention_until"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_evidence(record)
        await self._audit("evidence_recorded", actor, str(record["id"]), "APPROVED", {
            "case_id": record["case_id"], "legal_hold_id": record["legal_hold_id"],
        })
        await self.store.commit()
        return record

    async def retention_decision(self, evidence_id: str, now: Optional[str] = None) -> Dict[str, Any]:
        record = await self.store.get_evidence(evidence_id)
        if not record:
            raise core.IPLCIError("IPLCI_NOT_FOUND", "evidence not found")
        hold = await self.store.get_legal_hold(str(record.get("legal_hold_id"))) if record.get("legal_hold_id") else None
        decision = continuity.retention_decision(
            {**record, "under_legal_hold": bool(hold and not hold.get("released_at"))},
            now=now,
        )
        return {**decision, "evidence_id": evidence_id}

    async def continuity_check(self, state: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        audit = await self.audit()
        enriched = {
            "audit_chain_valid": audit["chain_valid"],
            **state,
        }
        result = continuity.continuity_check(enriched)
        record = {
            "id": str(uuid.uuid4()),
            "check_type": "governance_recovery",
            "risk": result["risk"],
            "outcome": result["outcome"],
            "problems": result["problems"],
            "recovery_actions": result["recovery_actions"],
            "payload": dict(state),
            "created_at": _now_iso(),
        }
        await self.store.put_continuity(record)
        await self._audit("continuity_checked", actor, record["id"], result["risk"], {
            "outcome": result["outcome"],
        })
        await self.store.commit()
        return {**result, "continuity_id": record["id"]}

    async def continuity_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        return await self.store.get_continuity(record_id)

    # --- Phase 6: signed policies and mandatory enforcement ---

    async def record_policy(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        version = str(payload.get("version") or "").strip()
        if not version:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "policy version is required")
        signer = str(payload.get("signed_by") or "").strip()
        approval_ref = str(payload.get("human_approval_reference") or "").strip()
        agent_like = ("iam", "main", "sdk", "system", "agent", "model", "creator_approval_pending")
        if (
            not signer
            or signer.lower() in agent_like
            or signer.lower().startswith(("sub-agent", "plugin:", "external_model:"))
            or not approval_ref
        ):
            raise core.IPLCIError(
                "IPLCI_HUMAN_APPROVAL_REQUIRED",
                "policy activation requires a human signer and a recorded approval reference",
            )
        current = await self.store.active_policy()
        proposed_rules = dict(payload.get("rules") or {})
        if current:
            relaxation = policy.check_relaxation(
                current,
                {"rules": proposed_rules, "status": "active"},
                human_approval_reference=payload.get("human_approval_reference"),
            )
            if not relaxation["permitted"]:
                raise core.IPLCIError(relaxation["error_code"], relaxation["reason"])
        document = policy.sign_policy(
            proposed_rules,
            version=version,
            signed_by=signer,
            signed_at=str(payload.get("signed_at") or _now_iso()),
        )
        if current:
            current["status"] = "retired"
            await self.store.put_policy(current)
        record = {
            "id": str(uuid.uuid4()),
            **document,
            "signed_at": document["signed_at"],
            "change_approval_ref": payload.get("human_approval_reference"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_policy(record)
        await self._audit("policy_signed", actor, record["id"], "APPROVED", {
            "version": version, "signed_by": document["signed_by"],
        })
        await self.store.commit()
        return record

    async def verify_active_policy(self) -> Dict[str, Any]:
        active = await self.store.active_policy()
        valid = policy.verify_policy(active)
        return {
            "domain": "legal_policy",
            "valid": valid,
            "version": active.get("version") if active else None,
            "signed_by": active.get("signed_by") if active else None,
            "status": "active" if valid else "unavailable",
            "policy_version": policy.POLICY_VERSION if hasattr(policy, "POLICY_VERSION") else "1.0",
        }

    async def check_policy_relaxation(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        current = await self.store.active_policy() or {}
        result = policy.check_relaxation(
            current,
            payload,
            human_approval_reference=payload.get("human_approval_reference"),
        )
        if not result["permitted"]:
            await self._audit("policy_relaxation_refused", actor, None, "CRITICAL", result)
            await self.store.commit()
        return result

    # --- Legal validation workflow (human/counsel completion track) ---

    async def open_validation_task(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        required = ("domain", "subject", "question")
        if any(not str(payload.get(field) or "").strip() for field in required):
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "domain, subject and question are required")
        record = {
            "id": str(uuid.uuid4()),
            "domain": payload["domain"],
            "subject": payload["subject"],
            "question": payload["question"],
            "jurisdiction": payload.get("jurisdiction"),
            "official_source_url": payload.get("official_source_url"),
            "provision_ref": payload.get("provision_ref"),
            "assigned_counsel": payload.get("assigned_counsel"),
            "status": "pending",
            "notes": payload.get("notes"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_validation_task(record)
        await self._audit("validation_task_opened", actor, record["id"], "QUARANTINED", {
            "domain": record["domain"], "subject": record["subject"],
        })
        await self.store.commit()
        return record

    async def record_validation_evidence(
        self, task_id: str, payload: Mapping[str, Any], actor: str = "sdk"
    ) -> Dict[str, Any]:
        record = await self.store.get_validation_task(task_id)
        if not record:
            raise core.IPLCIError("IPLCI_NOT_FOUND", "validation task not found")
        evidence = str(payload.get("evidence_ref") or "").strip()
        if not evidence:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "evidence_ref is required")
        record["evidence_ref"] = evidence
        record["assigned_counsel"] = payload.get("assigned_counsel") or record["assigned_counsel"]
        record["status"] = "in_review"
        await self.store.put_validation_task(record)
        await self._audit("validation_evidence_recorded", actor, task_id, "CONDITIONAL", {
            "evidence_ref": evidence,
        })
        await self.store.commit()
        return record

    async def verify_validation_task(
        self, task_id: str, payload: Mapping[str, Any], actor: str = "sdk"
    ) -> Dict[str, Any]:
        record = await self.store.get_validation_task(task_id)
        if not record:
            raise core.IPLCIError("IPLCI_NOT_FOUND", "validation task not found")
        reviewer = str(payload.get("reviewer_reference") or "").strip()
        agent_like = ("iam", "main", "sdk", "system", "agent", "model")
        if (
            not reviewer
            or reviewer.lower() in agent_like
            or reviewer.lower().startswith(("sub-agent", "plugin:", "external_model:"))
        ):
            raise core.IPLCIError(
                "IPLCI_COUNSEL_REQUIRED", "a qualified human reviewer reference is required"
            )
        if not record.get("evidence_ref"):
            raise core.IPLCIError("IPLCI_EVIDENCE_REQUIRED", "official-source evidence is required")
        record["status"] = "verified"
        record["reviewer_reference"] = reviewer
        record["reviewed_at"] = _now_iso()
        record["valid_until"] = payload.get("valid_until")
        if payload.get("official_source_url"):
            record["official_source_url"] = payload["official_source_url"]
        if payload.get("provision_ref"):
            record["provision_ref"] = payload["provision_ref"]
        await self.store.put_validation_task(record)
        await self._audit("validation_task_verified", actor, task_id, "APPROVED", {
            "reviewer_reference": reviewer, "valid_until": record["valid_until"],
        })
        await self.store.commit()
        return record

    async def validation_tasks(self) -> List[Dict[str, Any]]:
        return await self.store.list_validation_tasks()

    async def readiness_report(self) -> Dict[str, Any]:
        policy_status = await self.verify_active_policy()
        tasks = await self.store.list_validation_tasks()
        sources = await self.store.list_official_sources()
        blockers: List[str] = []
        if not policy_status["valid"]:
            blockers.append("no active signed compliance policy")
        if not tasks:
            blockers.append("no legal validation tasks exist; absence of evidence is not completion")
        unresolved = [task for task in tasks if task.get("status") != "verified"]
        if unresolved:
            blockers.append(f"{len(unresolved)} legal validation task(s) unresolved")
        unverified_sources = [source for source in sources if not source.get("verified_by")]
        if unverified_sources:
            blockers.append(f"{len(unverified_sources)} official source(s) unverified")
        return {
            "domain": "legal_readiness",
            "complete": not blockers,
            "blockers": blockers,
            "policy_valid": bool(policy_status["valid"]),
            "validation_tasks": len(tasks),
            "verified_tasks": len(tasks) - len(unresolved),
            "official_sources": len(sources),
            "adversarial_suite": "AT-01…AT-12 are CI-enforced; code is not a compliance claim",
            "legal_context_status": "requires_verification",
        }

    async def register_asset(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        title = str(payload.get("title") or "").strip()
        legal_owner = str(payload.get("legal_owner") or "").strip()
        if not title or not legal_owner:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "title and legal_owner are required")
        origin = payload.get("origin") or "iam"
        if origin not in ("iam", "creator", "third_party", "joint"):
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "invalid origin")
        record = {
            "id": str(uuid.uuid4()),
            "asset_type": payload.get("asset_type") or "software",
            "title": title,
            "created_by": payload.get("created_by") or actor,
            "legal_owner": legal_owner,
            "origin": origin,
            "inventorship": payload.get("inventorship"),
            "transfer_reference": payload.get("transfer_reference"),
            "third_party_contributions": list(payload.get("third_party_contributions") or []),
            "ownership_status": payload.get("ownership_status") or "unknown",
            "registration_status": payload.get("registration_status"),
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        await self.store.put_asset(record)
        await self._audit("ip_asset_registered", actor, record["id"], "APPROVED", {
            "legal_owner": legal_owner, "origin": origin,
        })
        await self.store.commit()
        return record

    async def register_dataset(self, payload: Mapping[str, Any], actor: str = "sdk") -> Dict[str, Any]:
        version = str(payload.get("dataset_version") or "").strip()
        if not version:
            raise core.IPLCIError("IPLCI_INVALID_INPUT", "dataset_version is required")
        record = {
            "id": str(uuid.uuid4()),
            "dataset_version": version,
            "source_ids": list(payload.get("source_ids") or []),
            "assessment_ids": list(payload.get("assessment_ids") or []),
            "collection_history": payload.get("collection_history"),
            "privacy_classification": payload.get("privacy_classification") or "unknown",
            "permitted_purposes": list(payload.get("permitted_purposes") or []),
            "retention_policy": payload.get("retention_policy"),
            "approval_status": "pending",
            "payload": dict(payload.get("payload") or {}),
            "created_at": _now_iso(),
        }
        await self.store.put_dataset(record)
        await self._audit("dataset_provenance_registered", actor, record["id"], "CONDITIONAL", {
            "dataset_version": version,
            "sources": record["source_ids"],
            "note": "training approval is separate and independent",
        })
        await self.store.commit()
        return record

    async def lineage(self, dataset_id: str) -> Dict[str, Any]:
        dataset = await self.store.get_dataset(dataset_id)
        if not dataset:
            raise core.IPLCIError("IPLCI_NOT_FOUND", "dataset not found")
        sources = []
        for source_id in dataset.get("source_ids") or []:
            source = await self.store.get_source(str(source_id))
            if source:
                sources.append({
                    "source_id": source_id,
                    "uri": source.get("uri"),
                    "rights_status": source.get("rights_status"),
                    "source_class": source.get("source_class"),
                    "current_permission_state": source.get("current_permission_state"),
                })
        assessments = []
        for assessment_id in dataset.get("assessment_ids") or []:
            assessment = await self.store.get_assessment(str(assessment_id))
            if assessment:
                assessments.append({
                    "assessment_id": assessment_id,
                    "decision": assessment.get("decision"),
                    "decision_class": assessment.get("decision_class"),
                    "operation": assessment.get("operation"),
                })
        return {"dataset": dataset, "sources": sources, "assessments": assessments}

    async def audit(self, limit: int = 100) -> Dict[str, Any]:
        events = await self.store.list_audit(limit)
        ascending = list(reversed(events))
        broken = core.verify_audit_chain(
            ascending,
            genesis_hash=ascending[0].get("previous_hash") if ascending else None,
        )
        return {
            "events": events,
            "chain_valid": not broken,
            "broken_event_ids": broken,
            "policy_version": core.POLICY_VERSION,
        }
