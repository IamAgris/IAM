"""P7-a — Curiosity / self-directed exploration engine.

IAM should be capable of identifying things worth understanding without always
waiting for a question or a detected contradiction. This engine scans IAM's own
shared epistemic state for knowledge gaps — low-confidence beliefs, unverified
beliefs, disputed beliefs, stale beliefs — and initiates legitimate research
into them:

    gap scan → curiosity hypothesis → independent verification → belief revision

Every step uses existing P0–P6 infrastructure:

* P2 hypothesis engine for counterfactual hypothesis generation
* P3 evidence service for persistent evidence and source credibility
* P4 learning engine for measured source-topic reliability
* P6 evaluation suite for whether the investigation actually improved anything

Nothing here is self-reported: hypotheses are verified against independent
evidence before beliefs are revised.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import uuid
import loguru

from app.services import iam_context
from app.services.evidence_service import EvidenceService
from app.services.research_service import research_service
from app.orchestration.hypothesis_engine import HypothesisRecord, HypothesisEngine
from app.orchestration.reasoning_engine import (
    ReasoningMode,
    ReasoningTrace,
    critique_reasoning,
    reason_in_mode,
)

logger = loguru.logger

STALE_BELIEF_HOURS = 72  # beliefs not reviewed in 72 hours are candidates
LOW_CONFIDENCE_THRESHOLD = 0.6
MAX_GAPS_PER_CYCLE = 10


@dataclass
class KnowledgeGap:
    """A gap in IAM's understanding identified by the curiosity scan."""

    id: str
    belief_id: Optional[str]  # None if no existing belief (pure gap)
    title: str
    content: str
    gap_type: str  # "unverified", "low_confidence", "disputed", "stale", "missing"
    current_confidence: float
    source: str
    topic: str
    reason: str
    discovered_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class CuriosityHypothesis:
    """A testable hypothesis generated from a knowledge gap."""

    id: str
    gap_id: str
    statement: str
    predicted_observation: str
    falsification_criterion: str
    verification_method: str  # "external_source", "logical_consistency", "experiment"
    status: str = "proposed"  # proposed | testing | confirmed | refuted | inconclusive
    confidence: float = 0.5
    evidence_for: List[Dict[str, Any]] = field(default_factory=list)
    evidence_against: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    belief_id: Optional[str] = None


class CuriosityEngine:
    """Scan IAM's beliefs for gaps and initiate independent investigation.

    Unlike P2 discovery (which starts from contradictions between beliefs),
    curiosity starts from IAM's own uncertainty: beliefs it hasn't verified,
    beliefs with low confidence, beliefs it hasn't revisited in a while, or
    topics it has almost no knowledge about.
    """

    async def scan_for_gaps(
        self,
        db: Any,
        *,
        limit: int = MAX_GAPS_PER_CYCLE,
    ) -> List[KnowledgeGap]:
        """Identify knowledge gaps in the shared epistemic state.

        A gap is any of:
        * an unverified belief (never independently confirmed)
        * a low-confidence belief (below LOW_CONFIDENCE_THRESHOLD)
        * a disputed belief (contradicted by another belief)
        * a stale belief (not reviewed in STALE_BELIEF_HOURS)
        * a topic with almost no beliefs at all (coverage gap)
        """
        beliefs = await iam_context.get_belief_state(db, limit=limit * 4)
        gaps: List[KnowledgeGap] = []
        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(hours=STALE_BELIEF_HOURS)

        for b in beliefs:
            last_reviewed = b.last_reviewed_at
            if last_reviewed:
                if isinstance(last_reviewed, str):
                    try:
                        last_reviewed = datetime.fromisoformat(last_reviewed)
                    except ValueError:
                        last_reviewed = None

            if b.verification_status == "unverified":
                gaps.append(
                    KnowledgeGap(
                        id=str(uuid.uuid4()),
                        belief_id=b.id,
                        title=b.title,
                        content=b.content,
                        gap_type="unverified",
                        current_confidence=b.confidence_level,
                        source=b.source,
                        topic=b.topic or "untopiced",
                        reason="belief has never been independently verified",
                    )
                )
            elif b.confidence_level < LOW_CONFIDENCE_THRESHOLD:
                gaps.append(
                    KnowledgeGap(
                        id=str(uuid.uuid4()),
                        belief_id=b.id,
                        title=b.title,
                        content=b.content,
                        gap_type="low_confidence",
                        current_confidence=b.confidence_level,
                        source=b.source,
                        topic=b.topic or "untopiced",
                        reason=f"confidence {b.confidence_level} below threshold {LOW_CONFIDENCE_THRESHOLD}",
                    )
                )
            elif b.verification_status == "disputed":
                gaps.append(
                    KnowledgeGap(
                        id=str(uuid.uuid4()),
                        belief_id=b.id,
                        title=b.title,
                        content=b.content,
                        gap_type="disputed",
                        current_confidence=b.confidence_level,
                        source=b.source,
                        topic=b.topic or "untopiced",
                        reason="belief is contradicted by another belief",
                    )
                )
            elif last_reviewed is not None and last_reviewed < stale_cutoff:
                gaps.append(
                    KnowledgeGap(
                        id=str(uuid.uuid4()),
                        belief_id=b.id,
                        title=b.title,
                        content=b.content,
                        gap_type="stale",
                        current_confidence=b.confidence_level,
                        source=b.source,
                        topic=b.topic or "untopiced",
                        reason=f"belief not reviewed in {STALE_BELIEF_HOURS} hours",
                    )
                )

        # Also detect coverage gaps: topics with very few beliefs
        topic_counts: Dict[str, int] = {}
        for b in beliefs:
            t = b.topic or "untopiced"
            topic_counts[t] = topic_counts.get(t, 0) + 1

        for topic, count in topic_counts.items():
            if count <= 1:
                gaps.append(
                    KnowledgeGap(
                        id=str(uuid.uuid4()),
                        belief_id=None,
                        title=f"Knowledge gap: {topic}",
                        content=f"IAM has only {count} belief(s) about {topic}.",
                        gap_type="coverage",
                        current_confidence=0.0,
                        source="curiosity_engine",
                        topic=topic,
                        reason="insufficient topic coverage",
                    )
                )

        # Sort by urgency: disputed > unverified > low_confidence > stale > coverage
        urgency = {"disputed": 0, "unverified": 1, "low_confidence": 2, "stale": 3, "coverage": 4}
        gaps.sort(key=lambda g: urgency.get(g.gap_type, 5))

        return gaps[:limit]

    async def generate_curiosity_hypothesis(
        self,
        db: Any,
        gap: KnowledgeGap,
    ) -> CuriosityHypothesis:
        """Generate a testable hypothesis from a knowledge gap using counterfactual reasoning.

        Unlike P2 discovery (contradiction-driven), curiosity asks: if this
        belief were true, what else would need to be true? Or if this belief
        is uncertain, what observation would settle it?
        """
        if gap.gap_type == "coverage":
            question = (
                f"IAM has almost no knowledge about {gap.topic}. "
                f"Propose ONE testable hypothesis about {gap.topic} that could be "
                f"independently verified. State the hypothesis, the observation "
                f"that would confirm it, and the observation that would falsify it."
            )
        else:
            question = (
                f"Knowledge gap: '{gap.title}' ({gap.gap_type}). "
                f"Current confidence: {gap.current_confidence}. "
                f"Reason: {gap.reason}. "
                f"Propose ONE testable hypothesis that resolves this uncertainty. "
                f"State the hypothesis, the observation that would confirm it, "
                f"and the observation that would falsify it."
            )

        try:
            trace = await reason_in_mode(
                None, ReasoningMode.COUNTERFACTUAL, question
            )
        except Exception as exc:
            logger.warning(f"curiosity hypothesis generation failed: {exc}")
            trace = None

        hypothesis = CuriosityHypothesis(
            id=str(uuid.uuid4()),
            gap_id=gap.id,
            statement=(
                trace.conclusion if trace else f"Hypothesis about {gap.title}"
            ),
            predicted_observation=(
                "; ".join(trace.reasoning_steps[:2])
                if trace and trace.reasoning_steps
                else "observation needed"
            ),
            falsification_criterion=(
                trace.identified_gaps[0]
                if trace and trace.identified_gaps
                else "no falsification criterion"
            ),
            verification_method="external_source",
            status="proposed",
            confidence=(
                trace.confidence if trace else 0.5
            ),
        )

        # Persist hypothesis as a belief in the shared epistemic state
        try:
            belief = await iam_context.record_belief(
                db,
                title=f"Curiosity hypothesis: {hypothesis.statement[:120]}",
                content=hypothesis.statement,
                source="curiosity_engine",
                confidence_level=hypothesis.confidence,
                topic=gap.topic or "curiosity",
                belief_type="hypothesis",
                provenance="curiosity_engine",
                evidence=[{
                    "type": "derived_from_knowledge_gap",
                    "gap_type": gap.gap_type,
                    "gap_reason": gap.reason,
                    "gap_belief_id": gap.belief_id,
                }],
            )
            hypothesis.belief_id = belief.id
        except Exception as exc:
            logger.warning(f"curiosity hypothesis persistence failed: {exc}")

        return hypothesis

    async def verify_curiosity_hypothesis(
        self,
        db: Any,
        hypothesis: CuriosityHypothesis,
    ) -> Dict[str, Any]:
        """Verify a curiosity hypothesis through independent evidence.

        Three independent checks, none self-reported:

        1. External sources via research service (ground truth)
        2. Cross-check against existing beliefs in shared epistemic state
        3. Adversarial critique using a different reasoning mode
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

        # Check 1: External sources via research service
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
                logger.warning(f"curiosity external verification failed: {exc}")
                record["external_verification"] = {"error": str(exc)}

        # Check 2: Cross-check against existing verified beliefs
        try:
            existing_contradictions = await iam_context.detect_contradictions(
                db, topic=hypothesis.belief_id and "", limit=20
            )
            # Filter contradictions relevant to this hypothesis
            for c in existing_contradictions:
                c_text = (
                    f"{c.get('belief_a', {}).get('title','')} "
                    f"{c.get('belief_b', {}).get('title','')}"
                ).lower()
                hyp_words = hypothesis.statement.lower().split()
                if any(w in c_text for w in hyp_words if len(w) > 4):
                    record["consistency_check"] = {
                        "contradicts_existing_belief": True,
                        "reason": c.get("reason"),
                    }
                    if record["final_status"] == "confirmed":
                        record["final_status"] = "inconclusive"
                        record["final_confidence"] = max(
                            0.0, record["final_confidence"] - 0.2
                        )
        except Exception as exc:
            logger.warning(f"curiosity consistency check failed: {exc}")

        # Check 3: Adversarial critique using counterfactual reasoning
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
            logger.warning(f"curiosity adversarial critique failed: {exc}")

        return record

    async def revise_belief_from_curiosity(
        self,
        db: Any,
        hypothesis: CuriosityHypothesis,
        verification: Dict[str, Any],
    ) -> bool:
        """Revise the shared epistemic state based on curiosity verification results."""
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
                    "type": "curiosity_verification",
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
            logger.warning(f"curiosity belief revision failed: {exc}")
            return False

    async def run_curiosity_cycle(
        self,
        db: Any,
    ) -> Dict[str, Any]:
        """Run one complete curiosity cycle: gap scan → hypothesise → verify → revise.

        Returns a summary of everything found and changed in this cycle.
        """
        summary: Dict[str, Any] = {
            "gaps_found": 0,
            "hypotheses_generated": 0,
            "hypotheses_verified": 0,
            "beliefs_confirmed": 0,
            "beliefs_refuted": 0,
            "beliefs_disputed": 0,
            "details": [],
        }

        # Step 1: Scan for knowledge gaps
        gaps = await self.scan_for_gaps(db, limit=MAX_GAPS_PER_CYCLE)
        summary["gaps_found"] = len(gaps)

        # Step 2: Generate hypotheses from gaps
        for gap in gaps:
            hypothesis = await self.generate_curiosity_hypothesis(db, gap)
            summary["hypotheses_generated"] += 1

            # Step 3: Verify each hypothesis independently
            verification = await self.verify_curiosity_hypothesis(db, hypothesis)
            summary["details"].append({
                "hypothesis_id": hypothesis.id,
                "gap_type": gap.gap_type,
                "statement": hypothesis.statement[:100],
                "final_status": verification["final_status"],
                "final_confidence": verification["final_confidence"],
            })

            # Step 4: Revise beliefs based on verification
            revised = await self.revise_belief_from_curiosity(
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
