"""Document 26 (OD-45): HBI Core orchestrator (Phase 1).

Enforces purpose/scope governance before analysis, preserves contradictions and
gaps, and refuses prediction when the capability is not validated (A8).
"""

import re
from typing import Any, Dict, List

from app.services.hbi import contradictions, gaps
from app.services.hbi.knowledge import KnowledgeStore
from app.services.hbi.schemas import (
    INDIVIDUAL_ALLOWED_PURPOSES,
    PROHIBITED_PURPOSES,
    AnalysisRequest,
    PredictionRequest,
    ResearchRequest,
)

_TOKEN = re.compile(r"[a-z]{4,}")


class GovernanceRefusal(Exception):
    def __init__(self, code: str, reason: str):
        super().__init__(reason)
        self.code = code
        self.reason = reason


class HBICore:
    def __init__(self, store: KnowledgeStore):
        self.store = store
        self.audit_log: List[Dict[str, Any]] = []

    def check_governance(self, purpose: str, scope: str) -> None:
        normalized = purpose.strip().lower().replace(" ", "_")
        if normalized in PROHIBITED_PURPOSES:
            raise GovernanceRefusal("PURPOSE_MISMATCH", f"prohibited_purpose::{normalized}")
        if scope == "individual" and normalized not in INDIVIDUAL_ALLOWED_PURPOSES:
            raise GovernanceRefusal("SCOPE_VIOLATION", "individual_scope_requires_consented_task")

    def _audit(self, event_type: str, purpose: str, scope: str, outcome: str, detail: Dict[str, Any]) -> None:
        entry = {
            "event_type": event_type, "purpose": purpose, "scope": scope,
            "outcome": outcome, "detail": detail,
        }
        self.audit_log.append(entry)
        if self.store.db is not None:
            from app.models.hbi import HBIAuditEvent
            self.store.db.add(HBIAuditEvent(**entry))
            # Audit writes are flushed, not committed here; the caller owns the transaction.

    def analyse(self, request: AnalysisRequest, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.check_governance(request.purpose, request.scope.value)
        tokens = set(_TOKEN.findall(request.question.lower()))
        matched = [
            r for r in records
            if r["scope"] == request.scope.value
            and (not tokens or any(t in r["claim"].lower() for t in tokens))
        ]
        if not matched:
            matched = [r for r in records if r["scope"] == request.scope.value]

        contradictions_result = contradictions.detect(self.store.claims())
        gap_result = gaps.detect(matched, request.question)
        weak = [r for r in matched if r["evidence_class"] in {"unverified", "speculation"}]
        avg_confidence = round(sum(r["confidence"] for r in matched) / len(matched), 2) if matched else 0.0

        refusal = None
        if not matched or len(weak) == len(matched) or avg_confidence < 0.5:
            refusal = {
                "code": "INSUFFICIENT_EVIDENCE",
                "reason": "cannot_reliably_analyse_with_current_evidence",
                "evidence_gaps": gap_result["gaps"],
                "what_would_change": [
                    "verified evidence from independent sources",
                    "context dimensions recorded for this question",
                    "reduction of detected contradictions",
                ],
            }

        result = {
            "question": request.question,
            "scope": request.scope.value,
            "epistemic_objects": [
                {
                    "record_ref": r["record_ref"],
                    "claim": r["claim"],
                    "epistemic_type": r["epistemic_type"],
                    "evidence_class": r["evidence_class"],
                    "confidence": r["confidence"],
                    "alternatives": r["alternatives"],
                    "causal_status": r["causal_status"],
                }
                for r in matched
            ],
            "contradictions": contradictions_result,
            "gaps": gap_result,
            "confidence": avg_confidence,
            "caveat": "Interpretations are possibilities, not psychological diagnoses or facts about a person.",
            "refusal": refusal,
        }
        self._audit("analysis", request.purpose, request.scope.value,
                    "refused" if refusal else "completed", {"question": request.question})
        return result

    def research(self, request: ResearchRequest, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.check_governance(request.purpose, request.scope.value)
        gap_result = gaps.detect(records, request.query)
        result = {
            "query": request.query,
            "scope": request.scope.value,
            "language": request.language,
            "period": request.period,
            "region": request.region,
            "gaps": gap_result["gaps"],
            "candidate_queries": [f"{request.query} — {g}" for g in gap_result["gaps"][:10]],
            "ingestion_status": "research_ingestion_engines_pending_phase_1",
            "note": "Candidates are research directions, not findings. Licence and provenance checks apply before ingestion.",
        }
        self._audit("research", request.purpose, request.scope.value, "completed", {"query": request.query})
        return result

    def predict(self, request: PredictionRequest, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        self.check_governance(request.purpose, request.scope.value)
        gap_result = gaps.detect(records, request.question)
        result = {
            "prediction_id": None,
            "target": request.target,
            "scope": request.scope.value,
            "time_horizon": request.time_horizon,
            "probability": {},
            "confidence": 0.0,
            "uncertainty": {"evidence_gap": "high", "model": "unvalidated", "distribution_shift": "unknown"},
            "refusal": {
                "code": "PREDICTION_SERVICE_NOT_VALIDATED",
                "reason": "A8_uncertainty_intelligence_prediction_withheld",
                "evidence_gaps": gap_result["gaps"],
                "what_would_change": [
                    "validated Prediction Service with calibration evidence",
                    "held-out evaluation and proper scoring results",
                    "governance approval for the declared purpose",
                ],
            },
            "note": "Probability and confidence are separate. No unverified forecast is emitted.",
        }
        self._audit("prediction", request.purpose, request.scope.value, "refused", {"target": request.target})
        return result
