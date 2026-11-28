"""Document 26 (OD-45): fail-closed corpus ingestion gate.

Public accessibility is not permission. A source enters the approved research
corpus only after licence, purpose, provenance, privacy/lawful-basis and
restriction checks pass. Copyright permission and POPIA/GDPR lawful basis are
separate requirements: satisfying one never satisfies the other.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.hbi.schemas import CorpusSourceManifest

ALLOWED_PURPOSES = {"research", "historical", "aggregate_analysis"}
PROHIBITED_PURPOSES = {"manipulation", "personal_use_only", "psychological_warfare", "targeting"}
_NOT_APPLICABLE = {"not_applicable", "", "none", "null"}


def evaluate(manifest: CorpusSourceManifest, intended_purpose: str,
             approved_by: str = "corpus_ingestion_gate",
             model_training: bool = False) -> Dict[str, Any]:
    """Run all gates; any rejection is fatal, any gap yields pending."""
    rejected: List[str] = []
    pending: List[str] = []
    checks: Dict[str, str] = {}
    rules = [
        "licence_verification", "purpose_verification", "provenance_verification",
        "privacy_and_lawful_basis_verification", "restriction_verification", "approval",
    ]

    # 1. Licence verification and compatibility.
    licence = manifest.licensing
    if not licence.licence_id and not licence.permission_evidence:
        rejected.append("licence_not_identified")
    elif licence.licence_id and not licence.licence_url and not licence.permission_evidence:
        pending.append("licence_url_or_permission_evidence_required")
    if licence.revocation_reference:
        rejected.append("licence_revoked")
    if licence.licence_expires_at:
        try:
            if date.fromisoformat(licence.licence_expires_at[:10]) < date.today():
                rejected.append("licence_expired")
        except ValueError:
            pending.append("licence_expiry_date_unparseable")
    if not (licence.ingestion_allowed and licence.storage_allowed and licence.analysis_allowed):
        rejected.append("licence_does_not_permit_required_processing")
    if model_training and not licence.model_training_allowed:
        rejected.append("research_permission_does_not_authorise_model_training")
    checks["licence_verification"] = "rejected" if any(r.startswith("licence") for r in rejected) or "research_permission_does_not_authorise_model_training" in rejected else "pending" if pending else "passed"

    # 2. Purpose verification — only the three declared identifiers are accepted.
    if intended_purpose in PROHIBITED_PURPOSES:
        rejected.append("prohibited_purpose")
    if intended_purpose not in ALLOWED_PURPOSES:
        rejected.append("unknown_purpose")
    elif intended_purpose not in manifest.permitted_purposes:
        rejected.append("purpose_not_permitted_by_source")
    outside = [p for p in manifest.permitted_purposes if p not in ALLOWED_PURPOSES]
    if outside:
        rejected.append("unapproved_purpose_listed")
    checks["purpose_verification"] = "rejected" if any("purpose" in r for r in rejected) else "passed"

    # 3. Provenance verification.
    provenance_ok = all([
        manifest.source_id,
        manifest.source.title,
        manifest.source.origin,
        manifest.source.collection_date,
    ])
    checks["provenance_verification"] = "passed" if provenance_ok else "pending"
    if not provenance_ok:
        pending.append("provenance_incomplete")

    # 4. Privacy and lawful basis — separate from copyright permission.
    privacy = manifest.privacy
    if privacy.sensitive_trait_inference or privacy.identifiable_profiles or privacy.contains_sensitive_personal_information:
        rejected.append("sensitive_processing_prohibited")
    basis = manifest.lawful_basis
    personal = privacy.contains_personal_information or basis.applies_to_living_persons
    if personal:
        if basis.basis.strip().lower() in _NOT_APPLICABLE:
            rejected.append("lawful_basis_missing")
        elif not basis.evidence_reference:
            pending.append("lawful_basis_evidence_required")
    checks["privacy_and_lawful_basis_verification"] = (
        "rejected" if any(r in {"sensitive_processing_prohibited", "lawful_basis_missing"} for r in rejected)
        else "pending" if "lawful_basis_evidence_required" in pending else "passed"
    )

    # 5. Restrictions.
    if manifest.governance.restrictions:
        rejected.append("source_restricted")
    checks["restriction_verification"] = "rejected" if "source_restricted" in rejected else "passed"

    # 6. Approval.
    if rejected:
        decision = "rejected"
    elif pending:
        decision = "pending"
    else:
        decision = "approved"
    checks["approval"] = decision

    return {
        "source_id": manifest.source_id,
        "decision": decision,
        "state": "validated" if decision == "approved" else "not_validated",
        "rejected_reasons": sorted(set(rejected)),
        "pending_reasons": sorted(set(pending)),
        "checks": checks,
        "rules_applied": rules,
        "intended_purpose": intended_purpose,
        "model_training": model_training,
        "approved_by": approved_by if decision == "approved" else None,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "licence_reference": licence.licence_id or licence.permission_evidence,
        "lawful_basis_reference": basis.evidence_reference,
        "note": "Copyright permission and POPIA/GDPR lawful basis are independent requirements.",
    }


class CorpusGovernance:
    """Durable-in-process registry of source decisions and audit history."""

    def __init__(self):  # type: ignore[no-untyped-def]
        self.decisions: Dict[str, Dict[str, Any]] = {}
        self.audit: List[Dict[str, Any]] = []

    def review(self, manifest: CorpusSourceManifest, intended_purpose: str = "research",
               approved_by: str = "corpus_ingestion_gate",
               model_training: bool = False) -> Dict[str, Any]:
        result = evaluate(manifest, intended_purpose, approved_by, model_training)
        self.decisions[manifest.source_id] = result
        self.audit.append({
            "source_id": manifest.source_id,
            "action": "review", "decision": result["decision"],
            "approved_by": result["approved_by"], "reviewed_at": result["reviewed_at"],
            "rules_applied": result["rules_applied"],
            "reasons": result["rejected_reasons"] + result["pending_reasons"],
        })
        return result

    def restrict(self, source_id: str, reason: str) -> Dict[str, Any]:
        record = self.decisions.get(source_id)
        if record is None:
            return {"restricted": False, "reason": "unknown_source"}
        record["state"] = "restricted"
        record["restriction_reason"] = reason
        self.audit.append({
            "source_id": source_id, "action": "restrict", "decision": "restricted",
            "approved_by": None, "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "rules_applied": ["restriction_verification"], "reasons": [reason],
        })
        return {"restricted": True, "source_id": source_id, "reason": reason}

    def approved_ids(self) -> set:  # type: ignore[type-arg]
        return {
            source_id for source_id, record in self.decisions.items()
            if record["decision"] == "approved" and record["state"] != "restricted"
        }

    def state(self) -> Dict[str, Any]:
        states = [record["state"] for record in self.decisions.values()]
        overall = "restricted" if "restricted" in states else "validated" if "validated" in states else "not_validated"
        return {
            "state": overall,
            "sources": len(states),
            "approved": sum(1 for r in self.decisions.values() if r["state"] == "validated"),
            "rejected": sum(1 for r in self.decisions.values() if r["decision"] == "rejected"),
            "pending": sum(1 for r in self.decisions.values() if r["decision"] == "pending"),
            "restricted": states.count("restricted"),
            "note": "Fail-closed: only approved sources enter the research corpus.",
        }

    def audit_history(self) -> Dict[str, Any]:
        return {"count": len(self.audit), "events": self.audit}
