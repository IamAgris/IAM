"""Hypothesis engine for P2 — converts contradictions into testable hypotheses
and verifies them through independent evidence.

Pipeline: contradiction → counterfactual hypothesis → independent
verification → belief revision.

Verification is NEVER self-reported: it uses external sources via the
research service, cross-checks against existing verified beliefs, and
applies a different reasoning mode than generation. IAM must not treat
its own generated explanations as proof that something is true.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import loguru

from app.services import iam_context
from app.services.research_service import research_service
from app.orchestration.reasoning_engine import (
    ReasoningMode,
    ReasoningTrace,
    critique_reasoning,
    reason_in_mode,
)

logger = loguru.logger


@dataclass
class HypothesisRecord:
    """A testable hypothesis derived from a contradiction or anomaly."""

    id: str
    statement: str
    derived_from: str  # e.g. "contradiction:{id_a}:{id_b}" or "anomaly:{source}"
    predicted_observation: str  # what would confirm this hypothesis
    falsification_criterion: str  # what would refute this hypothesis
    verification_method: str  # "external_source", "logical_consistency", "experiment"
    status: str  # "proposed", "testing", "confirmed", "refuted", "inconclusive"
    confidence: float
    evidence_for: List[Dict[str, Any]] = field(default_factory=list)
    evidence_against: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    belief_id: Optional[str] = None  # KnowledgeItem id in shared epistemic state


class HypothesisEngine:
    """Generate testable hypotheses from contradictions and anomalies.

    Converts detected contradictions into counterfactual hypotheses,
    designs verification experiments, routes through independent
    verification (external sources + different reasoning mode),
    and produces belief revisions in the shared epistemic state.
    """

    async def generate_from_contradictions(
        self,
        db: Any,
        contradictions: List[Dict[str, Any]],
    ) -> List[HypothesisRecord]:
        """Convert each detected contradiction into a testable hypothesis.

        Uses counterfactual reasoning: if one belief were false, what
        would need to be true for the other to hold? The resulting
        hypothesis carries a predicted observation and a falsification
        criterion so it can be independently verified.
        """
        hypotheses: List[HypothesisRecord] = []

        for c in contradictions:
            belief_a = c["belief_a"]
            belief_b = c["belief_b"]

            question = (
                f"Contradiction detected between two beliefs: "
                f"A) '{belief_a['title']}' ({belief_a['verification_status']}, "
                f"confidence {belief_a['confidence_level']}) and "
                f"B) '{belief_b['title']}' ({belief_b['verification_status']}, "
                f"confidence {belief_b['confidence_level']}). "
                f"Reason: {c.get('reason', 'unknown')}. "
                f"Propose ONE testable hypothesis that resolves this contradiction. "
                f"State the hypothesis, the observation that would confirm it, "
                f"and the observation that would falsify it."
            )

            try:
                trace = await reason_in_mode(
                    None, ReasoningMode.COUNTERFACTUAL, question
                )
            except Exception as exc:
                logger.warning(f"hypothesis generation failed: {exc}")
                continue

            hypothesis = HypothesisRecord(
                id=str(uuid.uuid4()),
                statement=trace.conclusion,
                derived_from=f"contradiction:{belief_a['id']}:{belief_b['id']}",
                predicted_observation=(
                    "; ".join(trace.reasoning_steps[:2])
                    if trace.reasoning_steps
                    else "observation needed"
                ),
                falsification_criterion=(
                    trace.identified_gaps[0] if trace.identified_gaps
                    else "no falsification criterion"
                ),
                verification_method="external_source",
                status="proposed",
                confidence=trace.confidence,
            )

            # Persist hypothesis as a belief in the shared epistemic state
            try:
                belief = await iam_context.record_belief(
                    db,
                    title=f"Hypothesis: {hypothesis.statement[:120]}",
                    content=hypothesis.statement,
                    source="hypothesis_engine",
                    confidence_level=hypothesis.confidence,
                    topic="hypothesis",
                    belief_type="hypothesis",
                    provenance="counterfactual_reasoning",
                    evidence=[{
                        "type": "derived_from_contradiction",
                        "contradiction_reason": c.get("reason"),
                        "belief_a_id": belief_a["id"],
                        "belief_b_id": belief_b["id"],
                    }],
                )
                hypothesis.belief_id = belief.id
            except Exception as exc:
                logger.warning(f"hypothesis persistence failed: {exc}")

            hypotheses.append(hypothesis)

        return hypotheses

    async def verify_independently(
        self,
        db: Any,
        hypothesis: HypothesisRecord,
    ) -> Dict[str, Any]:
        """Verify a hypothesis through independent evidence.

        Three independent checks, none of which is self-reported:

        1. External sources via the research service (ground truth from
           outside IAM's own generation).
        2. Cross-check against existing verified beliefs in the shared
           epistemic state (consistency with what IAM already holds).
        3. Adversarial critique using a different reasoning mode
           (dialectical, challenging the counterfactual generation).

        Returns a verification record with a final status that is never
        simply "the model said so."
        """
        record: Dict[str, Any] = {
            "hypothesis_id": hypothesis.id,
            "statement": hypothesis.statement,
            "external_verification": None,
            "consistency_check": None,
            "adversarial_critique": None,
            "final_status": "inconclusive",
            "final_confidence": hypothesis.confidence,
        }

        # Check 1: External sources via research service (ground truth)
        if hypothesis.belief_id:
            try:
                research = await research_service.verify_knowledge_against_sources(
                    hypothesis.belief_id
                )
                record["external_verification"] = research
                ext_status = research.get("verification_status")
                if ext_status == "verified":
                    record["final_status"] = "confirmed"
                    record["final_confidence"] = min(
                        1.0, hypothesis.confidence + 0.2
                    )
                elif ext_status == "disputed":
                    record["final_status"] = "refuted"
                    record["final_confidence"] = max(
                        0.0, hypothesis.confidence - 0.3
                    )
            except Exception as exc:
                logger.warning(f"external verification failed: {exc}")
                record["external_verification"] = {"error": str(exc)}

        # Check 2: Cross-check against existing verified beliefs
        try:
            existing_contradictions = await iam_context.detect_contradictions(
                db, topic="hypothesis", limit=20
            )
            for c in existing_contradictions:
                a_id = c.get("belief_a", {}).get("id", "")
                b_id = c.get("belief_b", {}).get("id", "")
                if hypothesis.id in (a_id, b_id):
                    record["consistency_check"] = {
                        "contradicts_existing_belief": True,
                        "reason": c.get("reason"),
                    }
                    # A verified belief contradicting our hypothesis weakens it
                    if record["final_status"] == "confirmed":
                        record["final_status"] = "inconclusive"
                        record["final_confidence"] = max(
                            0.0, record["final_confidence"] - 0.2
                        )
        except Exception as exc:
            logger.warning(f"consistency check failed: {exc}")

        # Check 3: Adversarial critique using a different reasoning mode
        try:
            trace_for_critique = ReasoningTrace(
                mode=ReasoningMode.COUNTERFACTUAL,
                question=hypothesis.statement,
                evidence=[],
                assumptions=[],
                reasoning_steps=[hypothesis.predicted_observation],
                conclusion=hypothesis.statement,
                confidence=hypothesis.confidence,
                contradictions=[],
                identified_gaps=[hypothesis.falsification_criterion],
            )
            critique = await critique_reasoning(None, trace_for_critique)
            record["adversarial_critique"] = critique
            if not critique.get("accept_conclusion", True):
                record["final_confidence"] = max(
                    0.0, record["final_confidence"] - 0.2
                )
                if record["final_status"] == "confirmed":
                    record["final_status"] = "inconclusive"
        except Exception as exc:
            logger.warning(f"adversarial critique failed: {exc}")

        return record

    async def revise_beliefs_from_verification(
        self,
        db: Any,
        hypothesis: HypothesisRecord,
        verification: Dict[str, Any],
    ) -> bool:
        """Revise the shared epistemic state based on verification results.

        Updates the hypothesis belief's verification status and confidence,
        appending the verification evidence to its review history so IAM
        can trace how its beliefs changed over time.
        """
        if not hypothesis.belief_id:
            return False

        final_status = verification.get("final_status", "inconclusive")
        final_confidence = verification.get(
            "final_confidence", hypothesis.confidence
        )

        new_status = "unverified"
        if final_status == "confirmed":
            new_status = "verified"
        elif final_status == "refuted":
            new_status = "refuted"
        elif final_status == "inconclusive":
            new_status = "disputed"

        try:
            await iam_context.revise_belief(
                db,
                hypothesis.belief_id,
                verification_status=new_status,
                confidence_level=final_confidence,
                evidence=[{
                    "type": "hypothesis_verification",
                    "final_status": final_status,
                    "external_verification": verification.get(
                        "external_verification"
                    ),
                    "consistency_check": verification.get("consistency_check"),
                    "adversarial_critique": verification.get(
                        "adversarial_critique"
                    ),
                }],
            )
            return True
        except Exception as exc:
            logger.warning(f"belief revision failed: {exc}")
            return False

    async def run_discovery_cycle(
        self,
        db: Any,
    ) -> Dict[str, Any]:
        """Run one complete discovery cycle: detect → hypothesise → verify → revise.

        Returns a summary of everything found and changed in this cycle.
        """
        summary: Dict[str, Any] = {
            "contradictions_found": 0,
            "hypotheses_generated": 0,
            "hypotheses_verified": 0,
            "beliefs_confirmed": 0,
            "beliefs_refuted": 0,
            "beliefs_disputed": 0,
            "details": [],
        }

        # Step 1: Detect contradictions in the shared epistemic state
        contradictions = await iam_context.detect_contradictions(db, limit=50)
        summary["contradictions_found"] = len(contradictions)

        # Step 2: Generate hypotheses from contradictions
        hypotheses = await self.generate_from_contradictions(db, contradictions)
        summary["hypotheses_generated"] = len(hypotheses)

        # Step 3: Verify each hypothesis independently
        for hypothesis in hypotheses:
            verification = await self.verify_independently(db, hypothesis)
            summary["details"].append({
                "hypothesis_id": hypothesis.id,
                "statement": hypothesis.statement[:100],
                "final_status": verification["final_status"],
                "final_confidence": verification["final_confidence"],
            })

            # Step 4: Revise beliefs based on verification
            revised = await self.revise_beliefs_from_verification(
                db, hypothesis, verification
            )
            if revised:
                summary["hypotheses_verified"] += 1
                fs = verification["final_status"]
                if fs == "confirmed":
                    summary["beliefs_confirmed"] += 1
                elif fs == "refuted":
                    summary["beliefs_refuted"] += 1
                elif fs == "inconclusive":
                    summary["beliefs_disputed"] += 1

        return summary
