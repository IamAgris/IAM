"""P7-e — Personal intellectual development history.

Aggregate roll-up of IAM's learning autobiography across topics over time.
Builds on P4's learning engine review_history data — every belief revision
is recorded with {status, confidence, at} timestamps, enabling IAM to trace
how its understanding has changed.

This is read-only: it summarizes existing belief revision history without
modifying anything. IAM can answer "what have I learned?", "when did I
change my mind about X?", "what was I wrong about?".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import loguru

from app.services import iam_context

logger = loguru.logger


@dataclass
class BeliefRevisionRecord:
    """A single revision of a belief over time."""

    belief_id: str
    title: str
    topic: str
    status: str
    confidence: float
    reviewed_at: str
    source: str


@dataclass
class TopicIntellectualHistory:
    """Intellectual development history for a single topic."""

    topic: str
    belief_count: int
    total_revisions: int
    current_status: str
    current_confidence: float
    first_belief_date: Optional[str]
    last_revision_date: Optional[str]
    revision_history: List[Dict[str, Any]]
    status_changes: List[Dict[str, Any]]  # when status flipped
    confidence_drift: float  # current - first confidence


@dataclass
class IntellectualDevelopmentHistory:
    """Aggregate view of IAM's intellectual development over time."""

    total_beliefs: int
    total_revisions: int
    beliefs_by_topic: Dict[str, int]
    beliefs_by_status: Dict[str, int]
    topic_histories: List[TopicIntellectualHistory]
    global_timeline: List[Dict[str, Any]]  # all revisions in chronological order
    major_revisions: List[Dict[str, Any]]  # status flips across all topics
    confidence_trend: List[Dict[str, Any]]  # average confidence over time
    time_span_days: float  # days between first and last revision


class IntellectualHistory:
    """Aggregate view of IAM's intellectual development.

    Reads belief revision history from the shared epistemic state and
    produces an aggregated view showing how IAM's understanding has
    changed over time. Read-only: does not modify any beliefs.
    """

    async def get_intellectual_history(
        self,
        db: Any,
        limit: int = 200,
    ) -> IntellectualDevelopmentHistory:
        """Get the complete intellectual development history.

        Reads all beliefs from the shared epistemic state, flattens their
        revision histories, and produces aggregate statistics.
        """
        beliefs = await iam_context.get_belief_state(db, limit=limit)

        topic_histories: Dict[str, TopicIntellectualHistory] = {}
        all_revisions: List[Dict[str, Any]] = []
        beliefs_by_status: Dict[str, int] = {}
        beliefs_by_topic: Dict[str, int] = {}

        total_revisions = 0

        for b in beliefs:
            topic = b.topic or "untopiced"
            beliefs_by_topic[topic] = beliefs_by_topic.get(topic, 0) + 1
            beliefs_by_status[b.verification_status or "unverified"] = (
                beliefs_by_status.get(b.verification_status or "unverified", 0) + 1
            )

            history = self._get_revision_history(b)
            total_revisions += len(history)

            # Build topic history
            if topic not in topic_histories:
                topic_histories[topic] = TopicIntellectualHistory(
                    topic=topic,
                    belief_count=0,
                    total_revisions=0,
                    current_status=b.verification_status or "unverified",
                    current_confidence=b.confidence_level or 0.5,
                    first_belief_date=None,
                    last_revision_date=None,
                    revision_history=[],
                    status_changes=[],
                    confidence_drift=0.0,
                )

            t = topic_histories[topic]
            t.belief_count += 1
            t.total_revisions += len(history)
            t.current_status = b.verification_status or "unverified"
            t.current_confidence = b.confidence_level or 0.5

            # Track all revisions with timestamps
            for entry in history:
                rev_entry = {
                    "belief_id": b.id,
                    "belief_title": b.title,
                    "topic": topic,
                    "status": entry.get("status", "unverified"),
                    "confidence": entry.get("confidence", 0.5),
                    "reviewed_at": entry.get("at", ""),
                }
                all_revisions.append(rev_entry)
                t.revision_history.append(rev_entry)

                # Track status changes
                if entry.get("status") in ("verified", "disputed", "refuted", "retracted"):
                    t.status_changes.append({
                        "belief_id": b.id,
                        "belief_title": b.title,
                        "status": entry.get("status"),
                        "reviewed_at": entry.get("at", ""),
                    })

            # Track dates
            created = b.created_at
            if created and isinstance(created, str):
                try:
                    created_dt = datetime.fromisoformat(created)
                except ValueError:
                    created_dt = None
            else:
                created_dt = None

            if t.first_belief_date is None or (
                created_dt and created_dt < datetime.fromisoformat(t.first_belief_date)
            ):
                t.first_belief_date = created

            last_rev = entry.get("at") if entry else None
            if last_rev and (
                t.last_revision_date is None
                or last_rev > t.last_revision_date
            ):
                t.last_revision_date = last_rev

        # Calculate confidence drift per topic
        for t in topic_histories.values():
            if t.revision_history:
                first_conf = t.revision_history[0].get("confidence", 0.5)
                last_conf = t.revision_history[-1].get("confidence", 0.5)
                t.confidence_drift = round(last_conf - first_conf, 4)

        # Sort topic histories by total revisions descending
        sorted_topics = sorted(
            topic_histories.values(),
            key=lambda t: t.total_revisions,
            reverse=True,
        )

        # Sort all revisions by date
        all_revisions.sort(key=lambda r: r.get("reviewed_at", ""))

        # Calculate global timeline
        global_timeline = all_revisions[:50]  # last 50 revisions

        # Calculate major revisions (status changes)
        major_revisions = [
            r for r in all_revisions
            if r.get("status") in ("verified", "disputed", "refuted", "retracted")
        ][:50]

        # Calculate confidence trend (average confidence per day)
        confidence_trend = self._calculate_confidence_trend(all_revisions)

        # Calculate time span
        time_span_days = 0.0
        if all_revisions:
            first_date = all_revisions[0].get("reviewed_at", "")
            last_date = all_revisions[-1].get("reviewed_at", "")
            if first_date and last_date:
                try:
                    first_dt = datetime.fromisoformat(first_date)
                    last_dt = datetime.fromisoformat(last_date)
                    time_span_days = (last_dt - first_dt).total_seconds() / 86400.0
                except ValueError:
                    pass

        return IntellectualDevelopmentHistory(
            total_beliefs=len(beliefs),
            total_revisions=total_revisions,
            beliefs_by_topic=beliefs_by_topic,
            beliefs_by_status=beliefs_by_status,
            topic_histories=[
                {
                    "topic": t.topic,
                    "belief_count": t.belief_count,
                    "total_revisions": t.total_revisions,
                    "current_status": t.current_status,
                    "current_confidence": t.current_confidence,
                    "first_belief_date": t.first_belief_date,
                    "last_revision_date": t.last_revision_date,
                    "revision_count": len(t.revision_history),
                    "status_change_count": len(t.status_changes),
                    "confidence_drift": t.confidence_drift,
                }
                for t in sorted_topics
            ],
            global_timeline=global_timeline,
            major_revisions=major_revisions,
            confidence_trend=confidence_trend,
            time_span_days=round(time_span_days, 2),
        )

    def _get_revision_history(self, b: Any) -> List[Dict[str, Any]]:
        """Extract revision history from a belief's metadata."""
        try:
            rh = getattr(b, "review_history", None)
            if rh is not None:
                return rh
            meta = getattr(b, "metadata_", None)
            return meta.get("review_history", []) if isinstance(meta, dict) else []
        except Exception:
            return []

    def _calculate_confidence_trend(
        self,
        revisions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Calculate average confidence over time from revision history."""
        if not revisions:
            return []

        # Group revisions by date
        daily: Dict[str, List[float]] = {}
        for r in revisions:
            date = r.get("reviewed_at", "")
            if date:
                try:
                    date_key = date[:10]  # YYYY-MM-DD
                except (ValueError, TypeError):
                    continue
                conf = r.get("confidence", 0.5)
                if conf is not None:
                    daily.setdefault(date_key, []).append(conf)

        trend: List[Dict[str, Any]] = []
        for date in sorted(daily.keys()):
            confs = daily[date]
            avg_conf = sum(confs) / len(confs)
            trend.append({
                "date": date,
                "average_confidence": round(avg_conf, 4),
                "revision_count": len(confs),
            })

        return trend

    async def get_learning_autobiography(
        self,
        db: Any,
    ) -> Dict[str, Any]:
        """Get a human-readable summary of IAM's intellectual development.

        Answers: what has IAM learned, when did it change its mind,
        what was it wrong about, what topics has it focused on?
        """
        history = await self.get_intellectual_history(db)

        # Identify major belief changes
        major_changes = [
            {
                "belief": r["belief_title"],
                "topic": r["topic"],
                "to_status": r["status"],
                "confidence": r["confidence"],
                "when": r["reviewed_at"],
            }
            for r in history.major_revisions[:10]
        ]

        # Identify topics with most change
        most_changed = sorted(
            history.topic_histories,
            key=lambda t: abs(t["confidence_drift"]),
            reverse=True,
        )[:5]

        # Identify stable beliefs (high confidence, verified)
        stable_beliefs = [
            {
                "topic": t["topic"],
                "status": t["current_status"],
                "confidence": t["current_confidence"],
            }
            for t in history.topic_histories
            if t["current_status"] == "verified" and t["current_confidence"] >= 0.8
        ][:5]

        return {
            "summary": {
                "total_beliefs": history.total_beliefs,
                "total_revisions": history.total_revisions,
                "time_span_days": history.time_span_days,
                "topics_tracked": len(history.topic_histories),
            },
            "major_changes": major_changes,
            "most_changed_topics": [
                {
                    "topic": t["topic"],
                    "confidence_drift": t["confidence_drift"],
                    "revisions": t["revision_count"],
                }
                for t in most_changed
            ],
            "stable_beliefs": stable_beliefs,
            "confidence_trend": history.confidence_trend,
        }
