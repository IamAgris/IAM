"""P7-b — Attention / cognitive resource management.

Decides what deserves IAM's cognitive effort. Instead of running every graph
node every cycle regardless of importance, attention scores candidates
(beliefs, contradictions, transfer opportunities, curiosity gaps) using
measured uncertainty and potential impact from P4 learning metrics, P5
cross-domain analysis, and P6 evaluation results.

The attention score is deterministic and auditable: it is never self-reported
importance, but derived from actual revision history, contradiction severity,
and evaluation performance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import loguru

from app.services import iam_context
from app.services.evidence_service import EvidenceService

logger = loguru.logger

MAX_ATTENTION_ITEMS_PER_CYCLE = 5
ATTENTION_BUDGET_TOKENS = 1000  # abstract cognitive budget per cycle


@dataclass
class AttentionItem:
    """A candidate for cognitive investment."""

    id: str
    kind: str  # "belief", "contradiction", "transfer", "gap"
    title: str
    attention_score: float  # 0.0 to 1.0
    reason: str
    source_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttentionDecision:
    """Result of attention allocation for one cycle."""

    total_budget: float
    allocated_tokens: float
    items: List[AttentionItem]
    skipped_count: int
    reason: str


class AttentionManager:
    """Allocate cognitive budget to the most valuable cognitive targets.

    Scoring is multiplicative: uncertainty × impact × recency. All inputs come
    from measured data (P4 revision history, P5 cross-domain contradictions,
    P6 evaluation trends), never from self-declared importance.
    """

    def __init__(self, db: Any):
        self.db = db

    async def allocate_attention(
        self,
        beliefs: Optional[List[Any]] = None,
        contradictions: Optional[List[Dict[str, Any]]] = None,
        transfers: Optional[List[Dict[str, Any]]] = None,
        gaps: Optional[List[Dict[str, Any]]] = None,
    ) -> AttentionDecision:
        """Allocate cognitive budget across candidate targets.

        Returns an AttentionDecision with the top-scoring items and how many
        tokens each receives. Items not in the top budget are skipped.
        """
        items: List[AttentionItem] = []

        # Score beliefs from P4 revision history
        if beliefs:
            for b in beliefs:
                score = await self._score_belief(b)
                if score > 0:
                    items.append(
                        AttentionItem(
                            id=f"belief:{b.id}",
                            kind="belief",
                            title=b.title,
                            attention_score=score,
                            reason=self._belief_score_reason(b),
                            source_data={
                                "belief_id": b.id,
                                "topic": b.topic,
                                "verification_status": b.verification_status,
                                "confidence_level": b.confidence_level,
                            },
                        )
                    )

        # Score contradictions from P5 cross-domain analysis
        if contradictions:
            for c in contradictions:
                score = self._score_contradiction(c)
                if score > 0:
                    items.append(
                        AttentionItem(
                            id=f"contradiction:{c.get('id', '')}",
                            kind="contradiction",
                            title=f"{c.get('belief_a_title', '')} vs {c.get('belief_b_title', '')}",
                            attention_score=score,
                            reason=c.get("reason", "cross-domain contradiction"),
                            source_data=c,
                        )
                    )

        # Score transfer opportunities from P5 cross-domain analysis
        if transfers:
            for t in transfers:
                score = self._score_transfer(t)
                if score > 0:
                    items.append(
                        AttentionItem(
                            id=f"transfer:{t.get('id', '')}",
                            kind="transfer",
                            title=t.get("insight", "")[:100],
                            attention_score=score,
                            reason=f"transfer from {t.get('source_topic', '')} to {t.get('target_topic', '')}",
                            source_data=t,
                        )
                    )

        # Score curiosity gaps from P7-a discovery
        if gaps:
            for g in gaps:
                score = self._score_gap(g)
                if score > 0:
                    items.append(
                        AttentionItem(
                            id=f"gap:{g.get('id', '')}",
                            kind="gap",
                            title=g.get("title", ""),
                            attention_score=score,
                            reason=g.get("reason", ""),
                            source_data=g,
                        )
                    )

        # Sort by attention score descending
        items.sort(key=lambda x: x.attention_score, reverse=True)

        # Allocate budget: top items get proportional tokens
        allocated: List[AttentionItem] = []
        remaining = ATTENTION_BUDGET_TOKENS
        skipped = 0

        for item in items:
            if remaining <= 0:
                skipped += 1
                continue
            # Allocate tokens proportional to score, minimum 50 tokens
            tokens = max(50, int(ATTENTION_BUDGET_TOKENS * item.attention_score))
            tokens = min(tokens, remaining)
            item.source_data["allocated_tokens"] = tokens
            allocated.append(item)
            remaining -= tokens

        return AttentionDecision(
            total_budget=ATTENTION_BUDGET_TOKENS,
            allocated_tokens=ATTENTION_BUDGET_TOKENS - remaining,
            items=allocated,
            skipped_count=skipped,
            reason="attention allocated by uncertainty × impact × recency",
        )

    # ------------------------------------------------------------------
    # Scoring functions
    # ------------------------------------------------------------------

    async def _score_belief(self, b: Any) -> float:
        """Score a belief for attention using P4 revision history.

        Score = uncertainty × impact × recency:
        * uncertainty: 1 - confidence (low confidence = high uncertainty)
        * impact: verification_status weight (disputed > unverified > verified)
        * recency: how recently the belief was created/reviewed
        """
        confidence = b.confidence_level or 0.5
        uncertainty = 1.0 - confidence

        status = (b.verification_status or "unverified").lower()
        impact = {
            "disputed": 1.0,
            "unverified": 0.8,
            "retracted": 0.6,
            "verified": 0.2,
            "expired": 0.1,
        }.get(status, 0.5)

        recency = self._belief_recency_score(b)

        score = uncertainty * impact * recency
        return round(max(0.0, min(1.0, score)), 4)

    def _belief_recency_score(self, b: Any) -> float:
        """Higher score for beliefs that are either very new (need attention)
        or very stale (need re-verification)."""
        now = datetime.now(timezone.utc)
        created = b.created_at
        reviewed = b.last_reviewed_at

        if created and isinstance(created, str):
            try:
                created = datetime.fromisoformat(created)
            except ValueError:
                created = None

        if reviewed and isinstance(reviewed, str):
            try:
                reviewed = datetime.fromisoformat(reviewed)
            except ValueError:
                reviewed = None

        # If never reviewed, high recency score
        if reviewed is None:
            return 1.0

        # Normalize both to timezone-aware
        if created and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if reviewed and reviewed.tzinfo is None:
            reviewed = reviewed.replace(tzinfo=timezone.utc)

        hours_since_review = float((now - reviewed).total_seconds() / 3600.0)

        # Beliefs reviewed in the last hour don't need attention
        if hours_since_review < 1:
            return 0.1

        # Beliefs not reviewed in 24+ hours need attention
        if hours_since_review > 24:
            return 1.0

        # Linear scale between 1 and 24 hours
        return 0.1 + 0.9 * (hours_since_review - 1) / 23.0

    def _belief_score_reason(self, b: Any) -> str:
        reasons = []
        if b.confidence_level and b.confidence_level < 0.6:
            reasons.append(f"low confidence ({b.confidence_level})")
        if b.verification_status == "disputed":
            reasons.append("disputed")
        elif b.verification_status == "unverified":
            reasons.append("unverified")
        if b.last_reviewed_at:
            try:
                reviewed = datetime.fromisoformat(str(b.last_reviewed_at))
                if reviewed.tzinfo is None:
                    reviewed = reviewed.replace(tzinfo=timezone.utc)
                hours = (datetime.now(timezone.utc) - reviewed).total_seconds() / 3600.0
                if hours > 24:
                    reasons.append(f"stale ({hours:.0f}h)")
            except (ValueError, TypeError):
                pass
        return "; ".join(reasons) if reasons else "routine"

    def _score_contradiction(self, c: Dict[str, Any]) -> float:
        """Score a cross-domain contradiction using P5 severity.

        Score = severity weight × confidence product of both beliefs.
        """
        severity_weights = {"high": 1.0, "medium": 0.6, "low": 0.3}
        severity = c.get("severity", "low")
        severity_score = severity_weights.get(severity, 0.3)

        conf_a = c.get("belief_a", {}).get("confidence_level", 0.5) or 0.5
        conf_b = c.get("belief_b", {}).get("confidence_level", 0.5) or 0.5
        confidence_product = conf_a * conf_b

        score = severity_score * confidence_product
        return round(max(0.0, min(1.0, score)), 4)

    def _score_transfer(self, t: Dict[str, Any]) -> float:
        """Score a cross-domain transfer opportunity using P5 viability.

        Score = transfer_confidence × (1 - method_compatibility_penalty).
        """
        confidence = t.get("transfer_confidence", 0.5) or 0.5
        viability = t.get("viability_score", 0.5) or 0.5

        # Higher viability = more worth paying attention to
        score = confidence * viability
        return round(max(0.0, min(1.0, score)), 4)

    def _score_gap(self, g: Dict[str, Any]) -> float:
        """Score a curiosity gap using P7-a urgency.

        Score based on gap_type urgency and current confidence.
        """
        urgency_weights = {
            "disputed": 1.0,
            "unverified": 0.9,
            "low_confidence": 0.8,
            "stale": 0.7,
            "coverage": 0.5,
        }
        urgency = urgency_weights.get(g.get("gap_type", "coverage"), 0.5)
        confidence = g.get("current_confidence", 0.5) or 0.5
        uncertainty = 1.0 - confidence

        score = urgency * uncertainty
        return round(max(0.0, min(1.0, score)), 4)

    async def get_attention_for_beliefs(
        self,
        db: Any,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get attention-scored beliefs from the shared epistemic state.

        Returns beliefs sorted by attention score, ready for the autonomy
        graph to decide which to investigate in this cycle.
        """
        beliefs = await iam_context.get_belief_state(db, limit=limit)
        items: List[Dict[str, Any]] = []

        for b in beliefs:
            score = await self._score_belief(b)
            if score > 0:
                items.append(
                    {
                        "belief_id": b.id,
                        "title": b.title,
                        "topic": b.topic,
                        "verification_status": b.verification_status,
                        "confidence_level": b.confidence_level,
                        "attention_score": score,
                        "reason": self._belief_score_reason(b),
                    }
                )

        items.sort(key=lambda x: x["attention_score"], reverse=True)
        return items
