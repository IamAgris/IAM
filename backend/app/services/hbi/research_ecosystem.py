"""Document 27 (proposed OD-47): Legal Research Intelligence Ecosystem.

Eight components with a central legal enforcement gate. Every action is checked
against the source classification (A-E); access never implies ownership.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

CHANNELS = [
    "open_access", "public_domain", "government_open_data", "university_partnership",
    "author_publisher_permission", "research_apis", "institutional_repositories",
    "licensed_commercial", "contributions", "synthetic", "own_research_lab",
    "federated_research",
]

DISCOVERY_TARGETS = [
    {"name": "openalex", "kind": "api", "note": "metadata; API terms and full-text rights differ"},
    {"name": "europe_pmc", "kind": "api", "note": "biomedical literature; check full-text rights"},
    {"name": "crossref", "kind": "api", "note": "scholarly metadata and DOI records"},
    {"name": "semantic_scholar", "kind": "api", "note": "discovery and citation metadata"},
    {"name": "wikidata", "kind": "api", "note": "structured facts; per-item terms"},
    {"name": "core", "kind": "repository", "note": "aggregated open-access research"},
    {"name": "base", "kind": "repository", "note": "academic repositories worldwide"},
    {"name": "doaj", "kind": "repository", "note": "open-access journals"},
    {"name": "openaire", "kind": "repository", "note": "European research outputs"},
    {"name": "harvard_dataverse", "kind": "repository", "note": "research datasets"},
    {"name": "icpsr", "kind": "repository", "note": "social and political science data"},
    {"name": "uk_data_service", "kind": "repository", "note": "population and social research"},
    {"name": "data_gov_za", "kind": "government", "note": "South African government datasets"},
    {"name": "unesco", "kind": "international", "note": "education, culture and social research"},
    {"name": "world_bank_open_data", "kind": "international", "note": "development and economic data"},
    {"name": "arxiv", "kind": "preprint", "note": "preprints are not automatically trainable"},
    {"name": "psyarxiv", "kind": "preprint", "note": "psychology preprints"},
    {"name": "socarxiv", "kind": "preprint", "note": "social science preprints"},
    {"name": "biorxiv", "kind": "preprint", "note": "biological and behavioural preprints"},
    {"name": "internet_archive", "kind": "archive", "note": "per-item rights"},
    {"name": "google_patents", "kind": "patent", "note": "patent documents and technical knowledge"},
]

ACTION_CLASSES = {
    "training": {"A"}, "analysis": {"A", "B"}, "retrieval": {"A", "B", "C"},
    "derive": {"A", "B"}, "retain": {"A", "B", "C"},
}


class ResearchEcosystem:
    def __init__(self, governance: Any, permissions: Any):
        self.governance = governance
        self.permissions = permissions
        self.targets = [
            {**target, "terms_status": "requires_verification", "verified_by": None,
             "verified_at": None, "reference": None}
            for target in DISCOVERY_TARGETS
        ]
        self.contributions: List[Dict[str, Any]] = []
        self.federated: List[Dict[str, Any]] = []
        self.lab_projects: List[Dict[str, Any]] = []
        self.audit: List[Dict[str, Any]] = []

    def _log(self, action: str, detail: Dict[str, Any], status: str) -> None:
        self.audit.append({
            "action": action, "status": status,
            "at": datetime.now(timezone.utc).isoformat(),
            **detail,
        })

    def channels(self) -> Dict[str, Any]:
        return {"count": len(CHANNELS), "channels": CHANNELS}

    def discovery_targets(self) -> Dict[str, Any]:
        return {"count": len(self.targets), "targets": self.targets,
                "note": "Every target requires a per-source rights assessment."}

    def verify_target(self, name: str, verified_by: str, reference: str) -> Dict[str, Any]:
        for target in self.targets:
            if target["name"] == name:
                target.update({"terms_status": "verified", "verified_by": verified_by,
                               "verified_at": datetime.now(timezone.utc).isoformat(),
                               "reference": reference})
                self._log("target_verification", {"name": name, "verified_by": verified_by}, "verified")
                return target
        return {"verified": False, "reason": "unknown_target"}

    def classify_source(self, source_id: str) -> Dict[str, Any]:
        decision = self.governance.decisions.get(source_id)
        manifest = self.permissions.manifests.get(source_id)
        if decision is None or manifest is None:
            return {"source_id": source_id, "classification": "D", "reason": "no_governance_decision"}
        if decision.get("decision") == "rejected" or decision.get("state") == "restricted":
            return {"source_id": source_id, "classification": "E", "reason": "prohibited_or_restricted"}
        if decision.get("decision") == "pending":
            return {"source_id": source_id, "classification": "D", "reason": "pending_verification"}
        if source_id in self.permissions.training_approved_ids():
            return {"source_id": source_id, "classification": "A", "reason": "training_approved"}
        if manifest.licensing.analysis_allowed:
            return {"source_id": source_id, "classification": "B", "reason": "analysis_approved"}
        return {"source_id": source_id, "classification": "C", "reason": "retrieval_only"}

    def enforce(self, source_id: str, action: str) -> Dict[str, Any]:
        classification = self.classify_source(source_id)["classification"]
        allowed = ACTION_CLASSES.get(action, set())
        permitted = classification in allowed
        self._log("enforcement", {"source_id": source_id, "action": action,
                                  "classification": classification},
                  "permitted" if permitted else "denied")
        return {
            "source_id": source_id, "action": action,
            "classification": classification, "permitted": permitted,
            "note": "Central legal gate; component behaviour cannot override it.",
        }

    def add_contribution(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        human_data = bool(payload.get("personal_data_present"))
        record = {
            **payload, "status": "pending", "ownership_retained": True,
            "requires_ethics_review": human_data,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }
        if human_data and not payload.get("ethics_reference"):
            record["status"] = "quarantined"
            record["reason"] = "ethics_reference_required"
        self.contributions.append(record)
        self._log("contribution", {"contributor": payload.get("contributor")}, record["status"])
        return record

    def list_contributions(self) -> Dict[str, Any]:
        return {"count": len(self.contributions), "contributions": self.contributions}

    def federated_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        record = {
            **payload, "status": "requested",
            "raw_data_transfer": False,
            "result_only": True,
        }
        self.federated.append(record)
        self._log("federated_request", {"institution": payload.get("institution")}, "requested")
        return record

    def federated_approve(self, institution: str, approver: str, reference: str) -> Dict[str, Any]:
        for record in self.federated:
            if record.get("institution") == institution:
                record.update({"status": "approved", "approved_by": approver,
                               "reference": reference, "raw_data_transfer": False})
                self._log("federated_approval", {"institution": institution}, "approved")
                return record
        return {"approved": False, "reason": "unknown_institution"}

    def lab_project(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        participants = bool(payload.get("human_participants"))
        record = {
            **payload, "status": "pending", "requires_ethics_review": participants,
        }
        if participants and not payload.get("ethics_reference"):
            record["status"] = "blocked"
            record["reason"] = "ethics_approval_required"
        self.lab_projects.append(record)
        self._log("lab_project", {"title": payload.get("title")}, record["status"])
        return record

    def transform(self, source_ids: List[str], output_type: str) -> Dict[str, Any]:
        checks = [self.enforce(source_id, "derive") for source_id in source_ids]
        blocked = [item["source_id"] for item in checks if not item["permitted"]]
        return {
            "output_type": output_type,
            "permitted": not blocked,
            "blocked_sources": blocked,
            "note": "Derived works can still carry source restrictions.",
        }

    def audit_history(self) -> Dict[str, Any]:
        return {"count": len(self.audit), "events": self.audit}
