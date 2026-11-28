"""Document 27 (proposed OD-47): original research laboratory.

Studies with human participants require ethics approval and informed consent.
Responses are stored under pseudonyms, consent is separable, and withdrawal
triggers deletion. No sensitive-trait inference or individual profiling occurs.
"""

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List

from app.services.hbi.schemas import (
    ParticipantConsentRequest,
    ParticipantWithdrawalRequest,
    StudyCreateRequest,
    StudyResponseRequest,
)


def _pseudonym(study_id: str, participant_ref: str) -> str:
    digest = hashlib.sha256(f"{study_id}:{participant_ref}".encode("utf-8")).hexdigest()
    return "part_" + digest[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchLab:
    def __init__(self) -> None:
        self.studies: Dict[str, Dict[str, Any]] = {}
        self.consents: Dict[str, Dict[str, Any]] = {}
        self.responses: List[Dict[str, Any]] = []
        self.audit: List[Dict[str, Any]] = []

    def _log(self, action: str, status: str, detail: Dict[str, Any]) -> None:
        self.audit.append({"action": action, "status": status, "at": _now(), **detail})

    def create_study(self, payload: StudyCreateRequest) -> Dict[str, Any]:
        study_id = "study_" + hashlib.sha256(
            f"{payload.title}:{payload.research_question}:{_now()}".encode("utf-8")
        ).hexdigest()[:12]
        blocked = payload.human_participants and not payload.ethics_reference
        record = {
            "study_id": study_id,
            "title": payload.title,
            "research_question": payload.research_question,
            "human_participants": payload.human_participants,
            "ethics_reference": payload.ethics_reference,
            "retention_days": payload.retention_days,
            "consent_purposes": payload.consent_purposes,
            "status": "blocked" if blocked else "approved",
            "created_at": _now(),
        }
        if blocked:
            record["reason"] = "ethics_approval_required"
        self.studies[study_id] = record
        self._log("study_created", str(record["status"]), {"study_id": study_id})
        return record

    def record_consent(self, payload: ParticipantConsentRequest) -> Dict[str, Any]:
        study = self.studies.get(payload.study_id)
        if study is None:
            return {"status": "rejected", "reason": "unknown_study"}
        if study["status"] != "approved":
            return {"status": "rejected", "reason": "study_not_approved"}
        purposes = payload.purposes or study["consent_purposes"]
        if not set(purposes).issubset(set(study["consent_purposes"])):
            return {"status": "rejected", "reason": "purpose_not_in_consent_scope"}
        pseudonym = _pseudonym(payload.study_id, payload.participant_ref)
        consent_id = "consent_" + hashlib.sha256(
            f"{pseudonym}:{_now()}".encode("utf-8")
        ).hexdigest()[:12]
        record = {
            "consent_id": consent_id,
            "study_id": payload.study_id,
            "pseudonym": pseudonym,
            "purposes": purposes,
            "basis": payload.basis,
            "retention_days": payload.retention_days or study["retention_days"],
            "granted_at": _now(),
            "withdrawn_at": None,
            "status": "active",
        }
        self.consents[consent_id] = record
        self._log("consent_recorded", "active", {"study_id": payload.study_id})
        return record

    def _active_consent(self, study_id: str, participant_ref: str) -> Dict[str, Any] | None:
        pseudonym = _pseudonym(study_id, participant_ref)
        for record in self.consents.values():
            if record["study_id"] == study_id and record["pseudonym"] == pseudonym and record["status"] == "active":
                return record
        return None

    def collect(self, payload: StudyResponseRequest) -> Dict[str, Any]:
        study = self.studies.get(payload.study_id)
        if study is None or study["status"] != "approved":
            return {"status": "rejected", "reason": "study_not_approved"}
        consent = self._active_consent(payload.study_id, payload.participant_ref)
        if consent is None:
            return {"status": "rejected", "reason": "active_consent_required"}
        if "research" not in consent["purposes"]:
            return {"status": "rejected", "reason": "research_not_in_consent_scope"}
        response = {
            "response_id": "resp_" + hashlib.sha256(
                f"{payload.study_id}:{payload.response}:{_now()}".encode("utf-8")
            ).hexdigest()[:12],
            "study_id": payload.study_id,
            "pseudonym": consent["pseudonym"],
            "consent_id": consent["consent_id"],
            "text": payload.response,
            "collected_at": _now(),
            "deleted": False,
        }
        self.responses.append(response)
        self._log("response_collected", "stored", {"study_id": payload.study_id})
        return {
            "response_id": response["response_id"],
            "pseudonym": response["pseudonym"],
            "status": "stored",
        }

    def withdraw(self, payload: ParticipantWithdrawalRequest) -> Dict[str, Any]:
        consent = self._active_consent(payload.study_id, payload.participant_ref)
        if consent is None:
            return {"withdrawn": False, "reason": "no_active_consent"}
        consent["status"] = "withdrawn"
        consent["withdrawn_at"] = _now()
        self._log("consent_withdrawn", "withdrawn", {"study_id": payload.study_id})
        return {
            "withdrawn": True,
            "consent_id": consent["consent_id"],
            "deletion_required": True,
            "reason": payload.reason,
        }

    def delete_responses(self, study_id: str, participant_ref: str) -> Dict[str, Any]:
        pseudonym = _pseudonym(study_id, participant_ref)
        removed = 0
        for response in self.responses:
            if response["study_id"] == study_id and response["pseudonym"] == pseudonym and not response["deleted"]:
                response["text"] = ""
                response["deleted"] = True
                removed += 1
        self._log("responses_deleted", "deleted", {"study_id": study_id, "removed": removed})
        return {"study_id": study_id, "responses_removed": removed}

    def report(self, study_id: str) -> Dict[str, Any]:
        study = self.studies.get(study_id)
        if study is None:
            return {"error": "unknown_study"}
        responses = [r for r in self.responses if r["study_id"] == study_id]
        consents = [c for c in self.consents.values() if c["study_id"] == study_id]
        return {
            "study_id": study_id,
            "status": study["status"],
            "ethics_reference": study["ethics_reference"],
            "consent_count": len(consents),
            "active_consents": sum(1 for c in consents if c["status"] == "active"),
            "response_count": len(responses),
            "deleted_responses": sum(1 for r in responses if r["deleted"]),
            "note": "Aggregate counts only; no individual profiles or sensitive traits.",
        }

    def audit_history(self) -> Dict[str, Any]:
        return {"count": len(self.audit), "events": self.audit}
