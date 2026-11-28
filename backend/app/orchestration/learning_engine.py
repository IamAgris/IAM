"""P4 — Learning and belief revision engine.

Analyzes the history of belief revisions to determine which reasoning
methods, sources, and topics actually produce confirmed knowledge —
replacing self-declared proficiency with measured learning.

The engine reads the shared epistemic state (KnowledgeItem rows with
review_history metadata) and computes:

* Longitudinal accuracy: do revised beliefs trend toward confirmation
  or refutation over time?
* Reasoning-method effectiveness: which modes (causal, analogical,
  counterfactual, probabilistic, dialectical, adversarial) lead to
  confirmed hypotheses?
* Source-topic reliability: which sources are trustworthy for which
  topics, empirically calibrated from revision outcomes.
* Revision stability: how often does a confirmed belief later get
  disputed or refuted?

Nothing here is self-reported: learning is computed from the actual
record of belief changes, not from IAM's own claims about its progress.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import loguru

from app.services import iam_context
from app.services.hbi.calibration import learn_source_weights

logger = loguru.logger


@dataclass
class BeliefRevision:
    """A single recorded revision of a belief."""

    belief_id: str
    title: str
    topic: str
    status: str  # verified | disputed | refuted | unverified | expired
    confidence: float
    reviewed_at: str
    source: str
    provenance: str


@dataclass
class LearningMetrics:
    """Aggregate learning metrics computed from belief revision history."""

    total_beliefs: int
    total_revisions: int
    confirmation_rate: float  # fraction of revisions ending in 'verified'
    refutation_rate: float  # fraction ending in 'refuted'
    dispute_rate: float  # fraction ending in 'disputed'
    stability_rate: float  # fraction of confirmed beliefs never later disputed
    average_confidence_change: float  # mean delta in confidence per revision
    reasoning_method_effectiveness: Dict[str, Dict[str, float]]
    source_topic_reliability: Dict[str, Dict[str, float]]
    topic_accuracy: Dict[str, Dict[str, float]]
    trends: List[Dict[str, Any]]


class LearningEngine:
    """Compute longitudinal learning metrics from belief revision history.

    Every method reads from the shared epistemic state — no self-reported
    learning claims are accepted. The engine asks: given the actual record
    of how IAM's beliefs have changed, which reasoning methods and sources
    produce knowledge that survives independent verification?
    """

    async def collect_revisions(
        self,
        db: Any,
        *,
        topic: Optional[str] = None,
        limit: int = 200,
    ) -> List[BeliefRevision]:
        """Collect all belief revision records from the shared epistemic state.

        Each belief's review_history contains a chronological list of
        {status, confidence, at} entries. We flatten those into
        BeliefRevision records for analysis.
        """
        beliefs = await iam_context.get_belief_state(
            db, topic=topic, limit=limit
        )
        revisions: List[BeliefRevision] = []

        for b in beliefs:
            history = self._get_review_history(b)
            for entry in history:
                revisions.append(
                    BeliefRevision(
                        belief_id=b.id,
                        title=b.title,
                        topic=b.topic or "untopiced",
                        status=entry.get("status", "unverified"),
                        confidence=entry.get("confidence", 0.5),
                        reviewed_at=entry.get("at", ""),
                        source=b.source,
                        provenance=b.provenance,
                    )
                )

        revisions.sort(key=lambda r: r.reviewed_at)
        return revisions

    def _get_review_history(self, belief: Any) -> List[Dict[str, Any]]:
        """Extract the review_history from a belief's metadata or dataclass."""
        try:
            # BeliefRecord may expose review_history directly
            rh = getattr(belief, "review_history", None)
            if rh is not None:
                return list(rh)
            # Fallback to KnowledgeItem-style metadata_
            meta = getattr(belief, "metadata_", None)
            return meta.get("review_history", []) if isinstance(meta, dict) else []
        except Exception:
            return []

    async def compute_metrics(
        self,
        db: Any,
        *,
        topic: Optional[str] = None,
        limit: int = 200,
    ) -> LearningMetrics:
        """Compute aggregate learning metrics from belief revision history."""
        revisions = await self.collect_revisions(
            db, topic=topic, limit=limit
        )

        total_beliefs = len(set(r.belief_id for r in revisions))
        total_revisions = len(revisions)

        if total_revisions == 0:
            return LearningMetrics(
                total_beliefs=total_beliefs,
                total_revisions=0,
                confirmation_rate=0.0,
                refutation_rate=0.0,
                dispute_rate=0.0,
                stability_rate=0.0,
                average_confidence_change=0.0,
                reasoning_method_effectiveness={},
                source_topic_reliability={},
                topic_accuracy={},
                trends=[],
            )

        confirmed = sum(1 for r in revisions if r.status == "verified")
        refuted = sum(1 for r in revisions if r.status == "refuted")
        disputed = sum(1 for r in revisions if r.status == "disputed")

        confirmation_rate = confirmed / total_revisions
        refutation_rate = refuted / total_revisions
        dispute_rate = disputed / total_revisions

        # Stability: confirmed beliefs that were never later disputed/refuted
        belief_statuses: Dict[str, List[str]] = {}
        for r in revisions:
            belief_statuses.setdefault(r.belief_id, []).append(r.status)
        stable = 0
        for bid, statuses in belief_statuses.items():
            if "verified" in statuses:
                # Check if 'verified' is the final status (no later dispute/refute)
                verified_indices = [
                    i for i, s in enumerate(statuses) if s == "verified"
                ]
                last_verified = max(verified_indices)
                after = statuses[last_verified + 1:]
                if not any(s in ("disputed", "refuted") for s in after):
                    stable += 1
        beliefs_with_verification = sum(
            1 for statuses in belief_statuses.values()
            if "verified" in statuses
        )
        stability_rate = stable / beliefs_with_verification if beliefs_with_verification else 0.0

        # Average confidence change per revision
        confidence_changes: List[float] = []
        belief_confidences: Dict[str, List[float]] = {}
        for r in revisions:
            belief_confidences.setdefault(r.belief_id, []).append(r.confidence)
        for bid, confs in belief_confidences.items():
            if len(confs) > 1:
                confidence_changes.append(confs[-1] - confs[0])
        avg_conf_change = (
            sum(confidence_changes) / len(confidence_changes)
            if confidence_changes
            else 0.0
        )

        # Reasoning-method effectiveness: from provenance field
        method_outcomes: Dict[str, Dict[str, int]] = {}
        for r in revisions:
            prov = r.provenance or "unknown"
            # Extract reasoning mode from provenance if present (e.g. "reasoning_engine:causal")
            method = prov.split(":")[-1] if ":" in prov else prov
            method_outcomes.setdefault(method, {"verified": 0, "refuted": 0, "disputed": 0, "total": 0})
            method_outcomes[method]["total"] += 1
            if r.status == "verified":
                method_outcomes[method]["verified"] += 1
            elif r.status == "refuted":
                method_outcomes[method]["refuted"] += 1
            elif r.status == "disputed":
                method_outcomes[method]["disputed"] += 1

        reasoning_effectiveness: Dict[str, Dict[str, float]] = {}
        for method, counts in method_outcomes.items():
            t = counts["total"]
            reasoning_effectiveness[method] = {
                "confirmation_rate": round(counts["verified"] / t, 3),
                "refutation_rate": round(counts["refuted"] / t, 3),
                "dispute_rate": round(counts["disputed"] / t, 3),
                "total_revisions": t,
            }

        # Source-topic reliability: empirically calibrated from revision outcomes
        source_topic_cases: List[Dict[str, Any]] = []
        for r in revisions:
            source_topic_cases.append({
                "source_type": r.source,
                "topic": r.topic,
                "outcome": 1 if r.status == "verified" else 0,
            })
        source_topic_reliability_raw = learn_source_weights(source_topic_cases)
        source_topic_reliability: Dict[str, Dict[str, float]] = {}
        for source_type, values in source_topic_reliability_raw.items():
            source_topic_reliability[source_type] = {
                "reliability": values["reliability"],
                "n": values["n"],
                "empirical": values["empirical"],
            }

        # Topic accuracy
        topic_outcomes: Dict[str, Dict[str, int]] = {}
        for r in revisions:
            topic_outcomes.setdefault(r.topic, {"verified": 0, "refuted": 0, "disputed": 0, "total": 0})
            topic_outcomes[r.topic]["total"] += 1
            if r.status == "verified":
                topic_outcomes[r.topic]["verified"] += 1
            elif r.status == "refuted":
                topic_outcomes[r.topic]["refuted"] += 1
            elif r.status == "disputed":
                topic_outcomes[r.topic]["disputed"] += 1

        topic_accuracy: Dict[str, Dict[str, float]] = {}
        for topic_name, counts in topic_outcomes.items():
            t = counts["total"]
            topic_accuracy[topic_name] = {
                "confirmation_rate": round(counts["verified"] / t, 3),
                "refutation_rate": round(counts["refuted"] / t, 3),
                "dispute_rate": round(counts["disputed"] / t, 3),
                "total_revisions": t,
            }

        # Trends: confirmation rate over time (buckets of revisions)
        trends: List[Dict[str, Any]] = []
        if total_revisions >= 10:
            bucket_size = max(1, total_revisions // 10)
            for i in range(0, total_revisions, bucket_size):
                bucket = revisions[i:i + bucket_size]
                if not bucket:
                    continue
                bucket_confirmed = sum(1 for r in bucket if r.status == "verified")
                trends.append({
                    "bucket": i // bucket_size,
                    "revisions": len(bucket),
                    "confirmation_rate": round(bucket_confirmed / len(bucket), 3),
                    "first_reviewed": bucket[0].reviewed_at,
                    "last_reviewed": bucket[-1].reviewed_at,
                })

        return LearningMetrics(
            total_beliefs=total_beliefs,
            total_revisions=total_revisions,
            confirmation_rate=round(confirmation_rate, 3),
            refutation_rate=round(refutation_rate, 3),
            dispute_rate=round(dispute_rate, 3),
            stability_rate=round(stability_rate, 3),
            average_confidence_change=round(avg_conf_change, 3),
            reasoning_method_effectiveness=reasoning_effectiveness,
            source_topic_reliability=source_topic_reliability,
            topic_accuracy=topic_accuracy,
            trends=trends,
        )

    async def learning_insights(
        self,
        metrics: LearningMetrics,
    ) -> List[Dict[str, Any]]:
        """Generate human-readable learning insights from metrics.

        These identify what IAM is actually learning vs what it merely
        claims to know.
        """
        insights: List[Dict[str, Any]] = []

        if metrics.total_revisions == 0:
            insights.append({
                "type": "no_data",
                "insight": "No belief revisions recorded yet — IAM has not yet revised any beliefs.",
                "severity": "info",
            })
            return insights

        # Confirmation vs refutation balance
        if metrics.refutation_rate > 0.3:
            insights.append({
                "type": "high_refutation",
                "insight": (
                    f"High refutation rate ({metrics.refutation_rate:.0%}): "
                    f"more than a third of revised beliefs are later refuted. "
                    f"IAM should lower confidence thresholds for new beliefs."
                ),
                "severity": "high",
            })
        elif metrics.confirmation_rate > 0.8 and metrics.stability_rate > 0.8:
            insights.append({
                "type": "stable_learning",
                "insight": (
                    f"Stable learning: {metrics.confirmation_rate:.0%} confirmation rate "
                    f"and {metrics.stability_rate:.0%} stability. Belief revisions "
                    f"are producing durable knowledge."
                ),
                "severity": "info",
            })

        # Reasoning method comparison
        best_method = None
        best_rate = 0.0
        for method, eff in metrics.reasoning_method_effectiveness.items():
            if eff["total_revisions"] >= 3 and eff["confirmation_rate"] > best_rate:
                best_rate = eff["confirmation_rate"]
                best_method = method
        if best_method:
            insights.append({
                "type": "best_reasoning_method",
                "insight": (
                    f"Most effective reasoning method: {best_method} "
                    f"({best_rate:.0%} confirmation over "
                    f"{metrics.reasoning_method_effectiveness[best_method]['total_revisions']} revisions)."
                ),
                "severity": "info",
            })

        # Worst method (avoid)
        worst_method = None
        worst_rate = 1.0
        for method, eff in metrics.reasoning_method_effectiveness.items():
            if eff["total_revisions"] >= 3 and eff["refutation_rate"] > worst_rate:
                worst_rate = eff["refutation_rate"]
                worst_method = method
        if worst_method:
            insights.append({
                "type": "worst_reasoning_method",
                "insight": (
                    f"Least reliable reasoning method: {worst_method} "
                    f"({worst_rate:.0%} refutation rate). "
                    f"Consider using it only with adversarial critique."
                ),
                "severity": "medium",
            })

        # Confidence trend
        if metrics.average_confidence_change > 0.05:
            insights.append({
                "type": "confidence_inflation",
                "insight": (
                    f"Average confidence increased by {metrics.average_confidence_change:.2f} "
                    f"per revision — IAM may be overconfident in its revisions."
                ),
                "severity": "medium",
            })
        elif metrics.average_confidence_change < -0.05:
            insights.append({
                "type": "confidence_calibration",
                "insight": (
                    f"Average confidence decreased by {abs(metrics.average_confidence_change):.2f} "
                    f"per revision — IAM is becoming better calibrated."
                ),
                "severity": "info",
            })

        # Trend direction
        if len(metrics.trends) >= 3:
            first_rate = metrics.trends[0]["confirmation_rate"]
            last_rate = metrics.trends[-1]["confirmation_rate"]
            if last_rate > first_rate + 0.1:
                insights.append({
                    "type": "improving_trend",
                    "insight": (
                        f"Confirmation rate improved from {first_rate:.0%} to {last_rate:.0%} "
                        f"over {len(metrics.trends)} revision buckets — learning is measurable."
                    ),
                    "severity": "info",
                })
            elif last_rate < first_rate - 0.1:
                insights.append({
                    "type": "declining_trend",
                    "insight": (
                        f"Confirmation rate declined from {first_rate:.0%} to {last_rate:.0%} "
                        f"— IAM's beliefs are becoming less reliable over time."
                    ),
                    "severity": "high",
                })

        return insights

    async def recommend_reasoning_method(
        self,
        db: Any,
        topic: str,
    ) -> Optional[str]:
        """Recommend the reasoning method with the best confirmation rate
        for a given topic, based on measured historical performance.

        Returns None if there is insufficient data.
        """
        metrics = await self.compute_metrics(db, topic=topic, limit=200)
        best_method = None
        best_score = 0.0
        for method, eff in metrics.reasoning_method_effectiveness.items():
            # Require at least 3 revisions for statistical significance
            if eff["total_revisions"] < 3:
                continue
            score = eff["confirmation_rate"] - eff["refutation_rate"]
            if score > best_score:
                best_score = score
                best_method = method
        return best_method

    async def sources_for_topic(
        self,
        db: Any,
        topic: str,
        min_reliability: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Return sources that are empirically reliable for a given topic.

        Only sources with empirical reliability (n >= 3) above the threshold
        are returned — no static priors.
        """
        metrics = await self.compute_metrics(db, topic=topic, limit=200)
        reliable: List[Dict[str, Any]] = []
        for source_type, values in metrics.source_topic_reliability.items():
            if values["empirical"] and values["reliability"] >= min_reliability:
                reliable.append({
                    "source_type": source_type,
                    "reliability": values["reliability"],
                    "n": values["n"],
                })
        reliable.sort(key=lambda x: x["reliability"], reverse=True)
        return reliable
