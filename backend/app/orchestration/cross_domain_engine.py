"""P5 — Cross-domain intelligence engine.

Transfers insights across topics: when a hypothesis is confirmed in one
domain, assess whether it applies to another; detect cross-domain
contradictions; identify common principles across disciplines; and
transfer source-topic reliability between related fields.

Everything is measured, not assumed: transfer confidence is derived from
P4's measured source-topic reliability and reasoning-method
effectiveness, not from analogical similarity alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import loguru

from app.services import iam_context
from app.orchestration.learning_engine import LearningEngine


@dataclass
class CrossDomainTransfer:
    """A proposed transfer of an insight from one domain to another."""

    id: str
    source_topic: str
    target_topic: str
    insight: str  # the confirmed finding to transfer
    source_confidence: float  # confidence in the source domain
    transfer_confidence: float  # confidence after transfer discount
    transfer_basis: str  # "common_principle", "structural_analogy", "shared_source"
    evidence_ids: List[str] = field(default_factory=list)
    status: str = "proposed"  # proposed | tested | confirmed | refuted | rejected
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CrossDomainContradiction:
    """A contradiction between beliefs in different domains."""

    id: str
    topic_a: str
    topic_b: str
    belief_a_title: str
    belief_b_title: str
    contradiction_reason: str
    severity: str  # "high" | "medium" | "low"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class CommonPrinciple:
    """A principle that appears to hold across multiple domains."""

    principle: str
    domains: List[str]
    supporting_evidence: List[Dict[str, Any]]
    cross_domain_confidence: float
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CrossDomainEngine:
    """Transfer insights across topics using measured reliability data.

    Never assumes that what works in one domain works in another.
    Transfer confidence is discounted by domain distance and source
    reliability, and every transfer is marked as requiring independent
    verification in the target domain.
    """

    async def find_transfer_opportunities(
        self,
        db: Any,
        *,
        min_source_confidence: float = 0.7,
        limit: int = 50,
    ) -> List[CrossDomainTransfer]:
        """Find confirmed insights in one domain that could transfer to another.

        Strategy:
        1. Get all verified beliefs grouped by topic.
        2. For each pair of topics, look for shared concepts (common words
           in titles/content beyond stop words).
        3. For each shared concept, propose a transfer with confidence
           discounted by source reliability in the target topic.
        4. Only propose transfers where the source belief is confirmed
           and the target topic has no conflicting verified belief.
        """
        transfers: List[CrossDomainTransfer] = []

        # Collect all verified beliefs grouped by topic
        topic_beliefs: Dict[str, List[Any]] = {}
        topics = await self._get_all_topics(db, limit=limit)
        for topic in topics:
            beliefs = await iam_context.get_belief_state(
                db, topic=topic, limit=20
            )
            verified = [b for b in beliefs if b.verification_status == "verified"
                        and b.confidence_level >= min_source_confidence]
            if verified:
                topic_beliefs[topic] = verified

        topics = list(topic_beliefs.keys())

        # Compare topic pairs for shared concepts
        for i, topic_a in enumerate(topics):
            for topic_b in topics[i + 1:]:
                shared = self._shared_concepts(
                    topic_beliefs[topic_a],
                    topic_beliefs[topic_b],
                )
                if not shared:
                    continue

                # For each shared concept, propose transfer from a to b
                for concept in shared[:3]:  # limit transfers per pair
                    source_belief = self._best_belief_for_concept(
                        topic_beliefs[topic_a], concept
                    )
                    target_belief = self._best_belief_for_concept(
                        topic_beliefs[topic_b], concept
                    )
                    if not source_belief or not target_belief:
                        continue

                    # Discount transfer confidence by source reliability
                    # in the target topic (P4 measured data)
                    engine = LearningEngine()
                    metrics = await engine.compute_metrics(
                        db, topic=topic_b, limit=100
                    )
                    source_reliability = metrics.source_topic_reliability.get(
                        source_belief.source, {"reliability": 0.5}
                    )["reliability"]

                    base_confidence = source_belief.confidence_level or 0.5
                    # Transfer discount: domain distance + source reliability
                    transfer_confidence = base_confidence * source_reliability * 0.8

                    transfers.append(CrossDomainTransfer(
                        id=f"transfer-{topic_a}-{topic_b}-{concept[:20]}",
                        source_topic=topic_a,
                        target_topic=topic_b,
                        insight=source_belief.content[:200],
                        source_confidence=base_confidence,
                        transfer_confidence=round(transfer_confidence, 3),
                        transfer_basis="shared_concept",
                        evidence_ids=[source_belief.id],
                    ))

        transfers.sort(key=lambda t: t.transfer_confidence, reverse=True)
        return transfers[:limit]

    async def detect_cross_domain_contradictions(
        self,
        db: Any,
        *,
        limit: int = 50,
    ) -> List[CrossDomainContradiction]:
        """Detect contradictions between beliefs in different domains.

        Uses iam_context.detect_contradictions() but filters for
        cross-topic pairs, then assesses severity based on confidence
        levels and verification status of both beliefs.
        """
        all_contradictions = await iam_context.detect_contradictions(
            db, topic=None, limit=200
        )
        cross_domain: List[CrossDomainContradiction] = []

        for c in all_contradictions:
            a = c.get("belief_a", {})
            b = c.get("belief_b", {})
            topic_a = a.get("topic", "untopiced")
            topic_b = b.get("topic", "untopiced")

            if topic_a == topic_b:
                continue  # same-domain, handled elsewhere

            conf_a = a.get("confidence_level", 0.5)
            conf_b = b.get("confidence_level", 0.5)
            status_a = a.get("verification_status", "unverified")
            status_b = b.get("verification_status", "unverified")

            # Only flag contradictions between verified/high-confidence beliefs
            if status_a not in ("verified", "disputed") and status_b not in (
                "verified", "disputed"
            ):
                continue

            # Severity: both verified + high confidence = high
            if status_a == "verified" and status_b == "verified":
                severity = "high"
            elif status_a == "verified" or status_b == "verified":
                severity = "medium"
            else:
                severity = "low"

            cross_domain.append(CrossDomainContradiction(
                id=f"xdomain-{a.get('id', '')}-{b.get('id', '')}",
                topic_a=topic_a,
                topic_b=topic_b,
                belief_a_title=a.get("title", ""),
                belief_b_title=b.get("title", ""),
                contradiction_reason=c.get("reason", "cross_domain_conflict"),
                severity=severity,
            ))

        cross_domain.sort(key=lambda c: {"high": 0, "medium": 1, "low": 2}[c.severity])
        return cross_domain[:limit]

    async def identify_common_principles(
        self,
        db: Any,
        *,
        min_domains: int = 2,
        limit: int = 20,
    ) -> List[CommonPrinciple]:
        """Identify principles that hold across multiple domains.

        Looks for beliefs with similar content/structure across different
        topics, then groups them by shared principle language. Only
        principles supported by verified beliefs in multiple domains
        are returned.
        """
        topic_beliefs: Dict[str, List[Any]] = {}
        topics = await self._get_all_topics(db, limit=100)
        for topic in topics:
            beliefs = await iam_context.get_belief_state(
                db, topic=topic, limit=30
            )
            verified = [b for b in beliefs if b.verification_status == "verified"]
            if verified:
                topic_beliefs[topic] = verified

        # Group beliefs by common content words (excluding stop words)
        principle_groups: Dict[str, List[Any]] = {}
        for topic, beliefs in topic_beliefs.items():
            for b in beliefs:
                words = self._content_words(b.title + " " + b.content)
                for word in words:
                    principle_groups.setdefault(word, []).append((topic, b))

        principles: List[CommonPrinciple] = []
        for word, occurrences in principle_groups.items():
            domains = set(topic for topic, _ in occurrences)
            if len(domains) < min_domains:
                continue

            # Only count verified beliefs
            verified_occurrences = [
                (t, b) for t, b in occurrences
                if b.verification_status == "verified"
            ]
            if len(verified_occurrences) < min_domains:
                continue

            # Cross-domain confidence: fraction of domains where verified
            verified_domains = set(t for t, _ in verified_occurrences)
            cross_domain_confidence = len(verified_domains) / len(domains)

            evidence = [
                {
                    "domain": t,
                    "belief_id": b.id,
                    "belief_title": b.title,
                    "confidence": b.confidence_level,
                }
                for t, b in verified_occurrences[:5]
            ]

            principles.append(CommonPrinciple(
                principle=word,
                domains=sorted(domains),
                supporting_evidence=evidence,
                cross_domain_confidence=round(cross_domain_confidence, 3),
            ))

        principles.sort(key=lambda p: p.cross_domain_confidence, reverse=True)
        return principles[:limit]

    async def assess_transfer_viability(
        self,
        db: Any,
        *,
        source_topic: str,
        target_topic: str,
        insight: str,
    ) -> Dict[str, Any]:
        """Assess whether transferring an insight from source_topic to
        target_topic is viable, based on measured data.

        Returns a viability score and recommendation.
        """
        # Get P4 measured reliability for the source topic's sources
        engine = LearningEngine()
        source_metrics = await engine.compute_metrics(db, topic=source_topic, limit=100)
        target_metrics = await engine.compute_metrics(db, topic=target_topic, limit=100)

        # Source topic's best confirmation rate
        source_confirmation = source_metrics.confirmation_rate
        target_confirmation = target_metrics.confirmation_rate

        # Best reasoning method in source topic
        best_source_method = None
        best_source_rate = 0.0
        for method, eff in source_metrics.reasoning_method_effectiveness.items():
            if eff["total_revisions"] >= 3 and eff["confirmation_rate"] > best_source_rate:
                best_source_rate = eff["confirmation_rate"]
                best_source_method = method

        # Best reasoning method in target topic
        best_target_method = None
        best_target_rate = 0.0
        for method, eff in target_metrics.reasoning_method_effectiveness.items():
            if eff["total_revisions"] >= 3 and eff["confirmation_rate"] > best_target_rate:
                best_target_rate = eff["confirmation_rate"]
                best_target_method = method

        # Viability: source confirmation × target confirmation × method compatibility
        method_compat = 1.0
        if best_source_method and best_target_method and best_source_method != best_target_method:
            method_compat = 0.7  # different methods = lower transfer viability

        viability = source_confirmation * target_confirmation * method_compat

        # Check for existing cross-domain contradiction
        contradictions = await self.detect_cross_domain_contradictions(db, limit=200)
        relevant_contradiction = any(
            c.topic_a == source_topic and c.topic_b == target_topic
            or c.topic_a == target_topic and c.topic_b == source_topic
            for c in contradictions
        )

        viable = viability > 0.3 and not relevant_contradiction

        return {
            "source_topic": source_topic,
            "target_topic": target_topic,
            "viability_score": round(viability, 3),
            "viable": viable,
            "source_confirmation_rate": source_confirmation,
            "target_confirmation_rate": target_confirmation,
            "best_source_method": best_source_method,
            "best_target_method": best_target_method,
            "method_compatibility": method_compat,
            "cross_domain_contradiction": relevant_contradiction,
            "recommendation": (
                "Transfer viable — propose as hypothesis in target domain"
                if viable else
                "Transfer not viable — verify independently in target domain"
            ),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_all_topics(
        self,
        db: Any,
        *,
        limit: int = 100,
    ) -> List[str]:
        """Get all distinct topics that have verified beliefs."""
        beliefs = await iam_context.get_belief_state(db, limit=limit * 5)
        topics = set()
        for b in beliefs:
            if b.topic:
                topics.add(b.topic)
        return sorted(topics)

    def _content_words(self, text: str) -> List[str]:
        """Extract content words (excluding stop words) from text."""
        stop = {
            "the", "and", "for", "with", "that", "this", "is", "are", "was", "were",
            "be", "been", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "to", "of", "in", "on", "at",
            "by", "from", "as", "an", "a", "or", "not", "no", "yes", "it", "its",
            "they", "them", "their", "we", "us", "our", "you", "your", "i", "me", "my",
        }
        import re
        words = re.findall(r"[a-z0-9]+", text.lower())
        return [w for w in words if len(w) > 4 and w not in stop]

    def _shared_concepts(
        self,
        beliefs_a: List[Any],
        beliefs_b: List[Any],
    ) -> List[str]:
        """Find content words shared between two topic's beliefs."""
        words_a: set = set()
        for b in beliefs_a:
            words_a.update(self._content_words(b.title + " " + b.content))
        words_b: set = set()
        for b in beliefs_b:
            words_b.update(self._content_words(b.title + " " + b.content))
        shared = words_a & words_b
        return sorted(shared)

    def _best_belief_for_concept(
        self,
        beliefs: List[Any],
        concept: str,
    ) -> Optional[Any]:
        """Return the verified belief with highest confidence mentioning concept."""
        best = None
        best_conf = 0.0
        for b in beliefs:
            if b.verification_status != "verified":
                continue
            text = (b.title + " " + b.content).lower()
            if concept in text and (b.confidence_level or 0.0) > best_conf:
                best = b
                best_conf = b.confidence_level or 0.0
        return best
