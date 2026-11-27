"""Document 27 (proposed OD-47): permission and acquisition engine.

Separates knowledge acquisition, knowledge intelligence and model development.
Training rights are never implied by ingestion approval and must be approved
by a reviewer independent of the ingestion reviewer.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List

from app.services.hbi.schemas import (
    CorpusSourceManifest,
    LegalContextVerificationRequest,
    PartnershipRequest,
    TrainingApprovalRequest,
    TrainingRequest,
)

ALLOWED_ACQUISITION_METHODS = {
    "open_access", "partnership", "direct_license", "public_domain", "synthetic"
}

LEGAL_TOPICS = [
    {
        "topic": "south_africa_copyright_amendment_bill_section_12A",
        "owner_supplied_note": "Constitutional Court judgment of 26 June 2026 addressed proposed fair-use section 12A; enactment and commencement status require verification.",
        "required_verification": "IP counsel must confirm current operative law before any reliance.",
    },
    {
        "topic": "popia_section_27_research",
        "owner_supplied_note": "Potential authorisation for special personal information processing for historical, statistical or research purposes, subject to conditions and safeguards.",
        "required_verification": "Confirm statutory text, conditions and safeguards with counsel.",
    },
    {
        "topic": "eu_tdm_article_4",
        "owner_supplied_note": "Directive 2019/790 Article 4 commercial TDM exception where rights are not appropriately reserved.",
        "required_verification": "Confirm territorial applicability and rights reservations.",
    },
    {
        "topic": "public_availability_is_not_permission",
        "owner_supplied_note": "Public accessibility does not remove copyright or POPIA/GDPR obligations.",
        "required_verification": "Confirm per source.",
    },
]


class PermissionEngine:
    def __init__(self, corpus_governance: Any):
        self.governance = corpus_governance
        self.manifests: Dict[str, CorpusSourceManifest] = {}
        self.training: Dict[str, Dict[str, Any]] = {}
        self.partnerships: List[Dict[str, Any]] = []
        self.legal_entries: Dict[str, Dict[str, Any]] = {}
        self.audit: List[Dict[str, Any]] = []
        for item in LEGAL_TOPICS:
            self.legal_entries[item["topic"].strip()] = {
                **item, "topic": item["topic"].strip(),
                "status": "requires_verification", "verified_by": None,
                "verified_at": None, "reference": None,
            }

    def register_manifest(self, manifest: CorpusSourceManifest) -> Dict[str, Any]:
        if manifest.acquisition_method not in ALLOWED_ACQUISITION_METHODS:
            return {"registered": False, "reason": "unknown_acquisition_method"}
        self.manifests[manifest.source_id] = manifest
        return {
            "registered": True, "source_id": manifest.source_id,
            "acquisition_method": manifest.acquisition_method,
            "rights_holder": manifest.rights_holder,
        }

    def request_training(self, payload: TrainingRequest) -> Dict[str, Any]:
        record = {
            "source_id": payload.source_id,
            "intended_model": payload.intended_model,
            "purpose": payload.purpose,
            "proposed_retention": payload.proposed_retention,
            "status": "pending",
        }
        self.training[payload.source_id] = record
        self.audit.append({"action": "training_request", "source_id": payload.source_id,
                           "status": "pending", "approved_by": None})
        return record

    def approve_training(self, payload: TrainingApprovalRequest) -> Dict[str, Any]:
        manifest = self.manifests.get(payload.source_id)
        record = self.training.get(payload.source_id)
        ingestion = self.governance.decisions.get(payload.source_id)
        blockers: List[str] = []

        if manifest is None:
            blockers.append("manifest_not_registered")
        if record is None:
            blockers.append("training_not_requested")
        if ingestion is None or ingestion.get("decision") != "approved":
            blockers.append("source_not_ingestion_approved")
        elif ingestion.get("state") == "restricted":
            blockers.append("source_restricted")
        if manifest is not None:
            licence = manifest.licensing
            if not licence.model_training_allowed:
                blockers.append("model_training_not_permitted")
            if not licence.derivative_allowed:
                blockers.append("derivatives_not_permitted")
            if not (licence.licence_id or licence.permission_evidence):
                blockers.append("permission_evidence_missing")
            purpose = (record or {}).get("purpose", "research")
            if purpose not in manifest.permitted_purposes:
                blockers.append("purpose_not_permitted")
            expiry = manifest.expiry_date or licence.licence_expires_at
            if expiry:
                try:
                    if date.fromisoformat(expiry[:10]) < date.today():
                        blockers.append("permission_expired")
                except ValueError:
                    blockers.append("expiry_unparseable")
            if manifest.revocation_conditions or licence.revocation_reference:
                blockers.append("revocation_present")
        if ingestion and ingestion.get("approved_by") == payload.approver:
            blockers.append("independent_approver_required")
        if payload.decision != "approved":
            blockers.append("not_an_approval")
        if not payload.basis:
            blockers.append("basis_required")

        decision = "approved" if not blockers else "rejected"
        timestamp = datetime.now(timezone.utc).isoformat()
        result = {
            "source_id": payload.source_id,
            "decision": decision,
            "blockers": blockers,
            "approved_by": payload.approver if decision == "approved" else None,
            "basis": payload.basis,
            "decided_at": timestamp,
            "note": "Training rights are independent of ingestion approval.",
        }
        if record is not None:
            record.update({"status": decision, "decision": result})
        self.audit.append({
            "action": "training_decision", "source_id": payload.source_id,
            "status": decision, "approved_by": result["approved_by"],
            "rules_applied": ["training_rights", "independent_approval", "restriction_and_expiry"],
            "reasons": blockers, "decided_at": timestamp,
        })
        return result

    def training_approved_ids(self) -> set:
        return {
            source_id for source_id, record in self.training.items()
            if record.get("status") == "approved"
            and self.governance.decisions.get(source_id, {}).get("state") != "restricted"
        }

    def add_partnership(self, payload: PartnershipRequest) -> Dict[str, Any]:
        record = {
            "organisation": payload.organisation,
            "contact_reference": payload.contact_reference,
            "requested_rights": payload.requested_rights,
            "safeguards": payload.safeguards,
            "agreement_reference": payload.agreement_reference,
            "status": "requested",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "requires_explicit_training_rights": "model_training" in payload.requested_rights,
        }
        self.partnerships.append(record)
        self.audit.append({"action": "partnership_request", "organisation": payload.organisation,
                           "status": "requested", "approved_by": None})
        return record

    def list_partnerships(self) -> Dict[str, Any]:
        return {"count": len(self.partnerships), "partnerships": self.partnerships}

    def legal_context(self) -> Dict[str, Any]:
        return {
            "entries": list(self.legal_entries.values()),
            "note": "Owner-supplied context; not legal advice. Unverified entries must not be relied on.",
        }

    def verify_legal_context(self, payload: LegalContextVerificationRequest) -> Dict[str, Any]:
        entry = self.legal_entries.get(payload.topic.strip())
        if entry is None:
            return {"verified": False, "reason": "unknown_topic"}
        entry.update({
            "status": "verified", "verified_by": payload.verified_by,
            "verified_at": datetime.now(timezone.utc).isoformat(),
            "reference": payload.reference,
        })
        self.audit.append({"action": "legal_context_verification", "topic": entry["topic"],
                           "status": "verified", "approved_by": payload.verified_by})
        return entry

    def audit_history(self) -> Dict[str, Any]:
        return {"count": len(self.audit), "events": self.audit}
