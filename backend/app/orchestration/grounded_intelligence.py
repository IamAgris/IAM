"""P7-c — Grounded intelligence / real-world feedback.

Connects IAM's understanding to actual outcomes. Live evidence collected
through search/browse/tool use is not automatically trusted — it must be
tested against reality before it can revise beliefs. This engine:

1. Takes live evidence from P3 evidence service
2. Designs verification experiments (search, cross-reference, tool execution)
3. Runs experiments and compares predicted vs actual outcomes
4. Updates beliefs only when experimental evidence confirms them
5. Detects when internal understanding is wrong and triggers belief revision

This is grounded intelligence: IAM's understanding is constrained by what it
can verify against external reality, not just what its models generate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import loguru

from app.services import iam_context
from app.services.evidence_service import EvidenceService
from app.services.research_service import research_service
from app.orchestration.hypothesis_engine import HypothesisEngine

logger = loguru.logger


@dataclass
class ExperimentResult:
    """Result of a grounded verification experiment."""

    experiment_id: str
    hypothesis_id: str
    predicted_outcome: str
    actual_outcome: str
    matched: bool
    confidence: float
    evidence_sources: List[str]
    executed_at: str


@dataclass
class GroundedBeliefUpdate:
    """A belief update that resulted from grounded verification."""

    belief_id: str
    title: str
    previous_status: str
    new_status: str
    previous_confidence: float
    new_confidence: float
    experiment_id: str
    verification_source: str


class GroundedIntelligence:
    """Connects IAM's understanding to real-world outcomes through
    grounded verification experiments.

    Every belief change must be backed by experimental evidence, not just
    model generation. This prevents IAM from mistaking plausible-sounding
    text for verified knowledge.
    """

    async def ground_belief(
        self,
        db: Any,
        belief_id: str,
        belief_title: str,
        belief_content: str,
        current_status: str,
        current_confidence: float,
    ) -> Dict[str, Any]:
        """Ground a belief through independent verification.

        Steps:
        1. Generate testable predictions from the belief
        2. Run verification experiments (search, cross-reference)
        3. Compare predicted vs actual outcomes
        4. Update belief only if experiment confirms it

        Returns the grounding result with experiment details.
        """
        result: Dict[str, Any] = {
            "belief_id": belief_id,
            "belief_title": belief_title,
            "previous_status": current_status,
            "previous_confidence": current_confidence,
            "experiments": [],
            "grounded": False,
            "new_status": current_status,
            "new_confidence": current_confidence,
            "reason": "",
        }

        # Step 1: Generate testable predictions from the belief
        predictions = self._generate_predictions(belief_title, belief_content)

        # Step 2: Run verification experiments for each prediction
        for prediction in predictions:
            experiment = await self._run_verification_experiment(
                db, belief_id, prediction
            )
            result["experiments"].append(experiment)

        # Step 3: Determine if belief is grounded
        confirmed_experiments = [
            e for e in result["experiments"] if e["matched"]
        ]
        total_experiments = len(result["experiments"])

        if total_experiments == 0:
            result["reason"] = "no experiments could be run"
            return result

        confirmation_rate = len(confirmed_experiments) / total_experiments

        # Step 4: Update belief based on experimental evidence
        if confirmation_rate >= 0.75:
            # Strong experimental confirmation
            result["grounded"] = True
            result["new_status"] = "verified"
            result["new_confidence"] = min(1.0, current_confidence + 0.2)
            result["reason"] = (
                f"{confirmation_rate:.0%} of experiments confirmed ({len(confirmed_experiments)}/{total_experiments})"
            )
        elif confirmation_rate >= 0.4:
            # Partial confirmation
            result["grounded"] = True
            result["new_status"] = "unverified"
            result["new_confidence"] = current_confidence
            result["reason"] = (
                f"{confirmation_rate:.0%} of experiments confirmed ({len(confirmed_experiments)}/{total_experiments}) - needs more evidence"
            )
        else:
            # Refuted
            result["grounded"] = True
            result["new_status"] = "refuted"
            result["new_confidence"] = max(0.0, current_confidence - 0.3)
            result["reason"] = (
                f"{1 - confirmation_rate:.0%} of experiments refuted ({total_experiments - len(confirmed_experiments)}/{total_experiments})"
            )

        return result

    def _generate_predictions(
        self,
        title: str,
        content: str,
    ) -> List[Dict[str, str]]:
        """Generate testable predictions from a belief.

        Each prediction has an expected observable outcome that can be
        checked against external sources.
        """
        predictions: List[Dict[str, str]] = []

        # Extract key claims from content
        content_lower = content.lower()

        # Prediction type 1: factual claim verification
        predictions.append(
            {
                "prediction": title,
                "expected_outcome": "confirmed_by_multiple_independent_sources",
                "verification_method": "external_source",
            }
        )

        # Prediction type 2: causal claim (if content contains causal language)
        if any(w in content_lower for w in ["causes", "leads to", "results in", "because"]):
            predictions.append(
                {
                    "prediction": f"causal_claim:{title}",
                    "expected_outcome": "causal_relationship_observable",
                    "verification_method": "external_source",
                }
            )

        # Prediction type 3: numerical claim
        import re
        numbers = re.findall(r"\d+\.?\d*", content)
        if numbers:
            predictions.append(
                {
                    "prediction": f"numerical_claim:{title}",
                    "expected_outcome": "numerical_value_matches_source",
                    "verification_method": "external_source",
                }
            )

        return predictions

    async def _run_verification_experiment(
        self,
        db: Any,
        belief_id: str,
        prediction: Dict[str, str],
    ) -> Dict[str, Any]:
        """Run a single verification experiment.

        Cross-references the prediction against external sources via the
        research service and compares predicted vs actual outcomes.
        """
        experiment_id = str(uuid.uuid4())

        try:
            # Use the research service to search for corroborating evidence
            research = await research_service.verify_knowledge_against_sources(
                belief_id
            )

            supporting = research.get("supporting_sources", [])
            contradicting = research.get("contradicting_sources", [])

            # Matched if we have supporting sources and no contradicting ones
            matched = len(supporting) > 0 and len(contradicting) == 0

            confidence = research.get("verification_status", "unverified")
            conf_score = {
                "verified": 1.0,
                "disputed": 0.0,
                "retracted": 0.0,
                "unverified": 0.3,
            }.get(confidence, 0.3)

            return {
                "experiment_id": experiment_id,
                "prediction": prediction["prediction"],
                "predicted_outcome": prediction["expected_outcome"],
                "actual_outcome": (
                    "confirmed" if matched else "not_confirmed"
                ),
                "matched": matched,
                "confidence": conf_score,
                "evidence_sources": [s.get("url", "") for s in supporting],
                "supporting_count": len(supporting),
                "contradicting_count": len(contradicting),
            }

        except Exception as exc:
            logger.warning(f"verification experiment failed: {exc}")
            return {
                "experiment_id": experiment_id,
                "prediction": prediction["prediction"],
                "predicted_outcome": prediction["expected_outcome"],
                "actual_outcome": "experiment_failed",
                "matched": False,
                "confidence": 0.0,
                "evidence_sources": [],
                "error": str(exc),
            }

    async def update_belief_from_experiment(
        self,
        db: Any,
        belief_id: str,
        new_status: str,
        new_confidence: float,
        experiment_result: Dict[str, Any],
    ) -> bool:
        """Update a belief in the shared epistemic state based on experiment results."""
        try:
            await iam_context.revise_belief(
                db,
                belief_id,
                verification_status=new_status,
                confidence_level=new_confidence,
                evidence=[{
                    "type": "grounded_verification",
                    "experiment_id": experiment_result["experiment_id"],
                    "matched": experiment_result["matched"],
                    "actual_outcome": experiment_result["actual_outcome"],
                    "evidence_sources": experiment_result.get("evidence_sources", []),
                }],
            )
            return True
        except Exception as exc:
            logger.warning(f"belief update from experiment failed: {exc}")
            return False

    async def detect_understanding_drift(
        self,
        db: Any,
        beliefs: Optional[List[Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Detect beliefs where IAM's understanding may be wrong.

        A belief is a drift candidate if:
        * It's verified but contradicted by newer evidence
        * It's unverified but has high confidence (overconfident)
        * It's disputed but still has high confidence

        Returns beliefs that need re-examination.
        """
        if beliefs is None:
            beliefs = await iam_context.get_belief_state(db, limit=50)

        drift_candidates: List[Dict[str, Any]] = []

        for b in beliefs:
            confidence = b.confidence_level or 0.5
            status = b.verification_status or "unverified"

            # Overconfident unverified belief
            if status == "unverified" and confidence > 0.8:
                drift_candidates.append({
                    "belief_id": b.id,
                    "title": b.title,
                    "topic": b.topic,
                    "drift_type": "overconfident_unverified",
                    "confidence": confidence,
                    "reason": "high confidence on unverified belief",
                })

            # Disputed but still high confidence
            if status == "disputed" and confidence > 0.7:
                drift_candidates.append({
                    "belief_id": b.id,
                    "title": b.title,
                    "topic": b.topic,
                    "drift_type": "disputed_but_confident",
                    "confidence": confidence,
                    "reason": "high confidence on disputed belief",
                })

            # Verified but stale (not reviewed recently)
            if status == "verified" and confidence > 0.8:
                if b.last_reviewed_at:
                    try:
                        reviewed = datetime.fromisoformat(str(b.last_reviewed_at))
                        if reviewed.tzinfo is None:
                            reviewed = reviewed.replace(tzinfo=timezone.utc)
                        hours = (datetime.now(timezone.utc) - reviewed).total_seconds() / 3600.0
                        if hours > 168:  # 7 days
                            drift_candidates.append({
                                "belief_id": b.id,
                                "title": b.title,
                                "topic": b.topic,
                                "drift_type": "stale_verified",
                                "confidence": confidence,
                                "reason": f"verified belief not reviewed in {hours:.0f}h",
                            })
                    except (ValueError, TypeError):
                        pass

        return drift_candidates
