"""Doc 17 / OD-33: tone and influence intelligence.

Defensive analysis of public text. Every output is a possible interpretation with
a confidence marker, never a psychological diagnosis or a claim about a person's
private mental state. The service does not generate influence content.
"""

import re
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.socialintel import ToneAnalysis

CAVEAT = (
    "Possible interpretations from text alone, not psychological diagnoses. "
    "Context may change the reading."
)

POSITIVE = {
    "good", "great", "excellent", "happy", "glad", "thanks", "thank", "love",
    "pleased", "excited", "wonderful", "helpful", "success", "nice", "appreciate",
}
NEGATIVE = {
    "bad", "terrible", "awful", "angry", "hate", "disappointed", "frustrated",
    "sad", "worried", "problem", "fail", "wrong", "useless", "annoyed", "poor",
}
AGGRESSION = {
    "idiot", "idiots", "stupid", "moron", "pathetic", "trash", "garbage", "dumb",
    "shut up", "jerk", "liar", "lying", "disgrace",
}
UNCERTAINTY = {
    "maybe", "perhaps", "might", "unsure", "uncertain", "doubt", "probably",
    "possibly", "not sure", "i think", "seems",
}
CERTAINTY_PRESSURE = {
    "obviously", "clearly", "everyone knows", "no doubt", "undoubtedly",
    "always", "never", "it is a fact", "without question",
}
FEAR = {
    "fear", "afraid", "dangerous", "threat", "crisis", "disaster", "collapse",
    "emergency", "scary", "destroy", "catastrophe", "panic",
}
SARCASM = {"/s", "yeah right", "sure thing", "thanks a lot", "great job", "as if"}
GASLIGHTING = {
    "you're imagining", "you are imagining", "you are crazy", "never happened",
    "you misremember", "delusional", "you made that up",
}
SCAPEGOATING = {"their fault", "to blame", "blame them", "traitor", "enemy", "outsiders"}
SOCIAL_PROOF = {"everyone", "everybody", "the majority", "all of us", "we all agree"}
URGENCY = {"act now", "immediately", "before it's too late", "urgent", "right now", "hurry"}
FORMAL = {"regards", "sincerely", "dear", "please", "kindly", "respectfully"}
INFORMAL = {"lol", "omg", "nah", "dude", "guys", "wtf", "tbh", "imo"}


def _hits(text: str, terms) -> List[str]:  # type: ignore[no-untyped-def]
    return sorted({term for term in terms if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text)})


class ToneService:
    """Heuristic tone and influence-pattern recognition for supplied text."""

    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db = db_session

    def analyse_text(self, text: str) -> Dict[str, Any]:
        """Analyse a single text. No external calls, no diagnoses."""
        lowered = text.lower()

        positive = _hits(lowered, POSITIVE)
        negative = _hits(lowered, NEGATIVE)
        aggression = _hits(lowered, AGGRESSION)
        uncertainty = _hits(lowered, UNCERTAINTY)
        certainty_pressure = _hits(lowered, CERTAINTY_PRESSURE)
        fear = _hits(lowered, FEAR)
        sarcasm = _hits(lowered, SARCASM)
        gaslighting = _hits(lowered, GASLIGHTING)
        scapegoating = _hits(lowered, SCAPEGOATING)
        social_proof = _hits(lowered, SOCIAL_PROOF)
        urgency = _hits(lowered, URGENCY)
        formal = _hits(lowered, FORMAL)
        informal = _hits(lowered, INFORMAL)

        sentiment = round(max(-1.0, min(1.0, (len(positive) - len(negative)) / 4.0)), 2)

        signals: List[Dict[str, str]] = []
        if aggression:
            signals.append({"pattern": "repeated aggressive language", "interpretation": "Hostile or confrontational tone"})
        if certainty_pressure:
            signals.append({"pattern": "excessive certainty without evidence", "interpretation": "Potential overconfidence or rhetorical pressure"})
        if fear:
            signals.append({"pattern": "repeated fear-based claims", "interpretation": "Possible fear-based persuasion"})
        if sarcasm:
            signals.append({"pattern": "sarcasm and irony", "interpretation": "Humour, criticism or indirect disagreement"})

        if aggression:
            tone = "hostile"
        elif fear:
            tone = "fearful"
        elif sarcasm:
            tone = "sarcastic"
        elif uncertainty and not positive:
            tone = "uncertain"
        elif sentiment >= 0.25:
            tone = "positive"
        elif sentiment <= -0.25:
            tone = "negative"
        else:
            tone = "neutral"

        if aggression:
            register = "confrontational"
        elif formal and len(formal) > len(informal):
            register = "formal"
        elif informal or positive:
            register = "friendly" if sentiment >= 0 else "informal"
        else:
            register = "informal"

        manipulation: List[str] = []
        if fear:
            manipulation.append("fear_based_messaging")
        if certainty_pressure:
            manipulation.append("certainty_pressure")
        if gaslighting:
            manipulation.append("gaslighting_pattern")
        if scapegoating:
            manipulation.append("scapegoating")
        if social_proof:
            manipulation.append("social_proof_appeal")
        if urgency:
            manipulation.append("urgency_pressure")

        confidence = round(min(0.9, 0.25 + 0.15 * len(signals) + 0.05 * len(manipulation)), 2)

        return {
            "tone": tone,
            "register": register,
            "sentiment": sentiment,
            "confidence": confidence,
            "signals": signals,
            "manipulation_indicators": manipulation,
            "interpretations": [s["interpretation"] for s in signals],
            "caveat": CAVEAT,
            "note": "No claim is made about any person's private psychological state.",
        }

    def analyse_discussion(self, texts: List[str]) -> Dict[str, Any]:
        """Analyse a discussion and flag possible style shifts between items."""
        analyses = [self.analyse_text(t) for t in texts]
        shifts: List[Dict[str, Any]] = []
        for index in range(1, len(analyses)):
            previous = analyses[index - 1]["tone"]
            current = analyses[index]["tone"]
            if previous != current:
                shifts.append({
                    "index": index,
                    "from": previous,
                    "to": current,
                    "interpretation": "Possible change in context or tone",
                })
        return {"analyses": analyses, "style_shifts": shifts, "caveat": CAVEAT}

    async def record_analysis(
        self,
        source_type: str,
        content_summary: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Persist an analysis as evidence with provenance markers."""
        if self.db is None:
            raise RuntimeError("Database session required to record an analysis")
        allowed_sources = {"message", "article", "post", "comment", "discussion", "text"}
        if source_type not in allowed_sources:
            raise ValueError("Invalid source_type")
        analysis = result or self.analyse_text(content_summary)
        record = ToneAnalysis(
            source_type=source_type,
            content_summary=content_summary[:2000],
            tone=analysis.get("tone", "neutral"),
            register=analysis.get("register", "informal"),
            sentiment=analysis.get("sentiment", 0.0),
            confidence=analysis.get("confidence", 0.0),
            signals=analysis.get("signals", []),
            manipulation_indicators=analysis.get("manipulation_indicators", []),
            interpretations=analysis.get("interpretations", []),
            caveat=analysis.get("caveat", CAVEAT),
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return {"id": str(record.id), "created_at": record.created_at.isoformat() if record.created_at else None}

    async def list_analyses(self, limit: int = 50) -> List[Dict[str, Any]]:
        if self.db is None:
            raise RuntimeError("Database session required to list analyses")
        result = await self.db.execute(
            select(ToneAnalysis).order_by(ToneAnalysis.created_at.desc()).limit(limit)
        )
        return [
            {
                "id": str(a.id),
                "source_type": a.source_type,
                "content_summary": a.content_summary,
                "tone": a.tone,
                "register": a.register,
                "sentiment": float(a.sentiment),
                "confidence": float(a.confidence),
                "signals": a.signals,
                "manipulation_indicators": a.manipulation_indicators,
                "interpretations": a.interpretations,
                "caveat": a.caveat,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in result.scalars().all()
        ]
