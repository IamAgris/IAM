"""P7-g — Knowledge uncertainty / intellectual honesty.

IAM should maintain an explicit "I don't know" state when confidence is low or
evidence is insufficient, and maintain competing hypotheses when evidence is
insufficient. This distinguishes between knowing something and merely believing
it knows something.

Builds on:
* P4 (confidence tracking per belief) — uses confidence scores to flag uncertainty
* P7-c (grounding verification) — uses verification results to assess reliability
* P6 (longitudinal evaluation) — tracks whether IAM's past confidence was calibrated

Key mechanisms:
* Uncertainty flags — mark beliefs where confidence is below threshold
* Competing hypotheses — maintain multiple competing conclusions when evidence
  is insufficient to decide between them
* Honest communication — surface uncertainty in responses rather than hiding it
* Mistake correction — track when IAM's past conclusions were wrong
* Calibration tracking — compare IAM's stated confidence against actual accuracy
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import loguru

from app.services import iam_context
from app.services.evidence_service import EvidenceService

logger = loguru.logger

LOW_CONFIDENCE_THRESHOLD = 0.6
UNCERTAINTY_CONFIDENCE_THRESHOLD = 0.4
MAX_COMPETING_HYPOTHESES = 5


@dataclass
class UncertaintyFlag:
    """An explicit "I don't know" marker on a belief or question."""

    id: str
    belief_id: Optional[str]
    question: str
    reason: str  # "low_confidence", "insufficient_evidence", "conflicting_evidence", "no_evidence"
    confidence: float
    evidence_gap: str  # what evidence is missing
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    resolved: bool = False
    resolved_at: Optional[str] = None


@dataclass
class CompetingHypothesis:
    """A competing explanation when evidence is insufficient to decide."""

    id: str
    question: str
    hypothesis: str
    confidence: float
    supporting_evidence: List[str]
    contradicting_evidence: List[str]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    resolved: bool = False
    winning_hypothesis: Optional[str] = None


@dataclass
class MistakeRecord:
    """A record of when IAM was wrong about something."""

    id: str
    belief_id: str
    original_conclusion: str
    original_confidence: float
    corrected_conclusion: str
    correction_reason: str
    discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class IntellectualHonesty:
    """Manage uncertainty, competing hypotheses, and intellectual honesty.

    IAM should:
    * Flag low-confidence beliefs as uncertain rather than presenting them as fact
    * Maintain competing hypotheses when evidence is insufficient
    * Communicate uncertainty honestly in responses
    * Track when past conclusions were wrong (mistake records)
    * Track whether stated confidence matches actual accuracy (calibration)
    """

    async def flag_uncertainty(
        self,
        db: Any,
        belief_id: str,
        question: str,
        reason: str,
        confidence: float,
        evidence_gap: str,
    ) -> UncertaintyFlag:
        """Flag a belief or question as uncertain.

        Creates an explicit "I don't know" marker that persists until the
        uncertainty is resolved through evidence.
        """
        flag = UncertaintyFlag(
            id=str(uuid.uuid4()),
            belief_id=belief_id,
            question=question,
            reason=reason,
            confidence=confidence,
            evidence_gap=evidence_gap,
        )

        # Record the uncertainty flag as a belief in the shared epistemic state
        try:
            await iam_context.record_belief(
                db,
                title=f"Uncertainty: {question[:100]}",
                content=f"I do not know: {question}. Reason: {reason}. Evidence gap: {evidence_gap}.",
                source="intellectual_honesty",
                confidence_level=confidence,
                topic="uncertainty",
                belief_type="uncertainty_flag",
                provenance="intellectual_honesty",
                evidence=[{
                    "type": "uncertainty_flag",
                    "reason": reason,
                    "evidence_gap": evidence_gap,
                    "confidence": confidence,
                }],
            )
        except Exception as exc:
            logger.warning(f"Uncertainty flag persistence failed: {exc}")

        logger.info(
            f"Uncertainty flag recorded: {question[:80]} (confidence={confidence})"
        )
        return flag

    async def maintain_competing_hypotheses(
        self,
        db: Any,
        question: str,
        hypotheses: List[Dict[str, Any]],
    ) -> List[CompetingHypothesis]:
        """Maintain multiple competing hypotheses when evidence is insufficient.

        When IAM cannot decide between multiple explanations, it should keep
        them all alive rather than prematurely committing to one.
        """
        hypotheses_records: List[CompetingHypothesis] = []

        for hyp in hypotheses[:MAX_COMPETING_HYPOTHESES]:
            record = CompetingHypothesis(
                id=str(uuid.uuid4()),
                question=question,
                hypothesis=hyp.get("hypothesis", ""),
                confidence=hyp.get("confidence", 0.5),
                supporting_evidence=hyp.get("supporting_evidence", []),
                contradicting_evidence=hyp.get("contradicting_evidence", []),
            )

            # Record the competing hypothesis as a belief
            try:
                await iam_context.record_belief(
                    db,
                    title=f"Competing hypothesis: {record.hypothesis[:100]}",
                    content=f"Competing explanation for '{question}': {record.hypothesis}",
                    source="intellectual_honesty",
                    confidence_level=record.confidence,
                    topic="uncertainty",
                    belief_type="competing_hypothesis",
                    provenance="intellectual_honesty",
                    evidence=[{
                        "type": "competing_hypothesis",
                        "question": question,
                        "supporting_evidence": record.supporting_evidence,
                        "contradicting_evidence": record.contradicting_evidence,
                    }],
                    contradicts=[],
                )
            except Exception as exc:
                logger.warning(f"Competing hypothesis persistence failed: {exc}")

            hypotheses_records.append(record)
            logger.info(
                f"Competing hypothesis recorded: {record.hypothesis[:80]} "
                f"(confidence={record.confidence})"
            )

        return hypotheses_records

    async def assess_uncertainty(
        self,
        db: Any,
        belief_id: str,
        belief_title: str,
        belief_content: str,
        current_status: str,
        current_confidence: float,
        evidence_count: int,
        contradicting_evidence_count: int,
    ) -> Dict[str, Any]:
        """Assess whether a belief should be flagged as uncertain.

        Returns an assessment with recommended action:
        - "confident" — high confidence, sufficient evidence
        - "uncertain" — low confidence or insufficient evidence → flag uncertainty
        - "competing" — conflicting evidence → maintain competing hypotheses
        - "grounded" — verified and well-supported
        """
        assessment: Dict[str, Any] = {
            "belief_id": belief_id,
            "belief_title": belief_title,
            "current_confidence": current_confidence,
            "current_status": current_status,
            "assessment": "grounded",
            "action": "none",
            "evidence_count": evidence_count,
            "contradicting_evidence_count": contradicting_evidence_count,
        }

        # Rule 1: Low confidence → uncertain
        if current_confidence < UNCERTAINTY_CONFIDENCE_THRESHOLD:
            assessment["assessment"] = "uncertain"
            assessment["action"] = "flag_uncertainty"
            assessment["reason"] = (
                f"Confidence {current_confidence} below threshold "
                f"{UNCERTAINTY_CONFIDENCE_THRESHOLD}"
            )
            return assessment

        # Rule 2: Contradicting evidence → competing hypotheses
        if contradicting_evidence_count > 0 and current_confidence < 0.8:
            assessment["assessment"] = "competing"
            assessment["action"] = "maintain_competing_hypotheses"
            assessment["reason"] = (
                f"{contradicting_evidence_count} contradicting evidence source(s) "
                f"with confidence {current_confidence}"
            )
            return assessment

        # Rule 3: Unverified but moderate confidence → uncertain
        if current_status == "unverified" and current_confidence < LOW_CONFIDENCE_THRESHOLD:
            assessment["assessment"] = "uncertain"
            assessment["action"] = "flag_uncertainty"
            assessment["reason"] = (
                "Unverified belief with moderate confidence"
            )
            return assessment

        # Rule 4: Verified and confident → grounded
        if current_status == "verified" and current_confidence >= LOW_CONFIDENCE_THRESHOLD:
            assessment["assessment"] = "grounded"
            assessment["action"] = "none"
            return assessment

        # Default: uncertain
        assessment["assessment"] = "uncertain"
        assessment["action"] = "flag_uncertainty"
        assessment["reason"] = "Insufficient evidence or confidence"
        return assessment

    async def record_mistake(
        self,
        db: Any,
        belief_id: str,
        original_conclusion: str,
        original_confidence: float,
        corrected_conclusion: str,
        correction_reason: str,
    ) -> MistakeRecord:
        """Record a mistake — when IAM was wrong about something.

        This is intellectual honesty: acknowledging when IAM's past conclusion
        was incorrect, so it can learn and avoid repeating the error.
        """
        record = MistakeRecord(
            id=str(uuid.uuid4()),
            belief_id=belief_id,
            original_conclusion=original_conclusion,
            original_confidence=original_confidence,
            corrected_conclusion=corrected_conclusion,
            correction_reason=correction_reason,
        )

        # Record the mistake as a belief in the shared epistemic state
        try:
            await iam_context.record_belief(
                db,
                title=f"Mistake corrected: {original_conclusion[:80]}",
                content=f"I was wrong: '{original_conclusion}'. Correct: '{corrected_conclusion}'. Reason: {correction_reason}.",
                source="intellectual_honesty",
                confidence_level=0.9,
                topic="mistake_correction",
                belief_type="mistake_record",
                provenance="intellectual_honesty",
                evidence=[{
                    "type": "mistake_correction",
                    "original_conclusion": original_conclusion,
                    "original_confidence": original_confidence,
                    "corrected_conclusion": corrected_conclusion,
                    "correction_reason": correction_reason,
                }],
            )
        except Exception as exc:
            logger.warning(f"Mistake record persistence failed: {exc}")

        logger.info(
            f"Mistake recorded: '{original_conclusion}' → '{corrected_conclusion}'"
        )
        return record

    async def assess_calibration(
        self,
        db: Any,
        beliefs: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Assess whether IAM's stated confidence matches actual accuracy.

        Compares confidence levels against verification outcomes:
        - Well-calibrated: high-confidence beliefs are verified, low-confidence
          beliefs are uncertain
        - Overconfident: high-confidence beliefs are disputed/refuted
        - Underconfident: low-confidence beliefs are verified
        """
        if beliefs is None:
            beliefs = await iam_context.get_belief_state(db, limit=200)

        total = len(beliefs)
        if total == 0:
            return {
                "total_beliefs": 0,
                "calibration_score": 0.0,
                "assessment": "no_data",
                "overconfident_count": 0,
                "underconfident_count": 0,
                "well_calibrated_count": 0,
            }

        well_calibrated = 0
        overconfident = 0
        underconfident = 0

        for b in beliefs:
            confidence = b.confidence_level or 0.5
            status = b.verification_status or "unverified"

            if status == "verified" and confidence >= 0.7:
                well_calibrated += 1
            elif status in ("disputed", "refuted") and confidence >= 0.7:
                overconfident += 1
            elif status == "verified" and confidence < 0.4:
                underconfident += 1

        calibration_score = well_calibrated / total if total > 0 else 0.0

        if calibration_score >= 0.7:
            assessment = "well_calibrated"
        elif calibration_score >= 0.4:
            assessment = "moderately_calibrated"
        else:
            assessment = "poorly_calibrated"

        return {
            "total_beliefs": total,
            "calibration_score": round(calibration_score, 4),
            "assessment": assessment,
            "well_calibrated_count": well_calibrated,
            "overconfident_count": overconfident,
            "underconfident_count": underconfident,
        }

    async def honest_response_assessment(
        self,
        db: Any,
        question: str,
        proposed_answer: str,
        proposed_confidence: float,
        supporting_evidence_count: int,
        contradicting_evidence_count: int,
    ) -> Dict[str, Any]:
        """Assess whether IAM should communicate uncertainty honestly.

        Returns whether IAM should say "I don't know" or express uncertainty,
        and what confidence level to communicate.
        """
        # Rule 1: Very low confidence → say "I don't know"
        if proposed_confidence < UNCERTAINTY_CONFIDENCE_THRESHOLD:
            return {
                "should_communicate_uncertainty": True,
                "uncertainty_level": "high",
                "recommended_response": "I don't know",
                "recommended_confidence": proposed_confidence,
                "reason": f"Confidence {proposed_confidence} below uncertainty threshold",
            }

        # Rule 2: Contradicting evidence → express uncertainty
        if contradicting_evidence_count > 0 and proposed_confidence < 0.7:
            return {
                "should_communicate_uncertainty": True,
                "uncertainty_level": "medium",
                "recommended_response": "I'm not certain",
                "recommended_confidence": proposed_confidence,
                "reason": (
                    f"{contradicting_evidence_count} contradicting evidence source(s)"
                ),
            }

        # Rule 3: Low supporting evidence → express uncertainty
        if supporting_evidence_count == 0 and proposed_confidence < LOW_CONFIDENCE_THRESHOLD:
            return {
                "should_communicate_uncertainty": True,
                "uncertainty_level": "medium",
                "recommended_response": "I have limited evidence",
                "recommended_confidence": proposed_confidence,
                "reason": "No supporting evidence",
            }

        # Rule 4: High confidence, sufficient evidence → communicate confidently
        if proposed_confidence >= LOW_CONFIDENCE_THRESHOLD and supporting_evidence_count > 0:
            return {
                "should_communicate_uncertainty": False,
                "uncertainty_level": "low",
                "recommended_response": proposed_answer,
                "recommended_confidence": proposed_confidence,
                "reason": "Sufficient evidence and confidence",
            }

        # Default: express some uncertainty
        return {
            "should_communicate_uncertainty": True,
            "uncertainty_level": "low",
            "recommended_response": "I believe, but I'm not certain",
            "recommended_confidence": proposed_confidence,
            "reason": "Limited evidence or confidence",
        }

    async def run_intellectual_honesty_cycle(
        self,
        db: Any,
        beliefs: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Run one complete intellectual honesty cycle.

        Flags uncertain beliefs, maintains competing hypotheses, records
        mistakes, and assesses calibration.
        """
        if beliefs is None:
            beliefs = await iam_context.get_belief_state(db, limit=200)

        summary: Dict[str, Any] = {
            "uncertainty_flags": 0,
            "competing_hypotheses": 0,
            "mistakes_recorded": 0,
            "calibration": {},
            "details": [],
        }

        # Step 1: Assess each belief for uncertainty
        for b in beliefs:
            assessment = await self.assess_uncertainty(
                db,
                belief_id=b.id,
                belief_title=b.title,
                belief_content=b.content,
                current_status=b.verification_status or "unverified",
                current_confidence=b.confidence_level or 0.5,
                evidence_count=0,  # would come from evidence service
                contradicting_evidence_count=0,  # would come from contradiction detection
            )

            if assessment["action"] == "flag_uncertainty":
                await self.flag_uncertainty(
                    db,
                    belief_id=b.id,
                    question=b.title,
                    reason=assessment["reason"],
                    confidence=b.confidence_level or 0.5,
                    evidence_gap="insufficient evidence",
                )
                summary["uncertainty_flags"] += 1
                summary["details"].append({
                    "belief_id": b.id,
                    "title": b.title,
                    "action": "flag_uncertainty",
                    "reason": assessment["reason"],
                })

        # Step 2: Assess calibration
        calibration = await self.assess_calibration(db, beliefs)
        summary["calibration"] = calibration

        return summary
