"""Document 26 (OD-45): module 14 — psychological threat and manipulation
intelligence. DEFENSIVE ONLY: recognises patterns so people can identify and
resist them. It never generates influence content or targeting guidance.
"""

import re
from typing import Any, Dict, List

_PATTERNS = {
    "fear_based_messaging": {"crisis", "danger", "destroy", "catastrophe", "panic", "threat"},
    "urgency_pressure": {"act now", "immediately", "before it's too late", "urgent", "hurry"},
    "certainty_pressure": {"obviously", "everyone knows", "no doubt", "without question"},
    "scapegoating": {"their fault", "to blame", "traitor", "enemy", "outsiders"},
    "social_proof_pressure": {"everyone agrees", "all of us", "the majority"},
    "gaslighting_pattern": {"you are imagining", "never happened", "you misremember", "delusional"},
    "false_authority": {"as an expert", "official sources confirm", "scientists agree"},
    "us_vs_them": {"they want to", "our people", "their kind", "enemies of"},
}
_INTERPRETATIONS = {
    "fear_based_messaging": "possible fear-based framing",
    "urgency_pressure": "possible pressure to decide without deliberation",
    "certainty_pressure": "possible rhetorical certainty without evidence",
    "scapegoating": "possible blame attribution to an out-group",
    "social_proof_pressure": "possible appeal to conformity",
    "gaslighting_pattern": "possible attempt to undermine another person's recollection",
    "false_authority": "possible unverifiable authority claim",
    "us_vs_them": "possible in-group/out-group framing",
}
_CAVEAT = (
    "Pattern recognition only. These are possible interpretations of language, "
    "not diagnoses, proof of intent, or instructions for influencing anyone."
)


def _hits(text: str, terms) -> List[str]:  # type: ignore[no-untyped-def]
    lowered = text.lower()
    return sorted({term for term in terms if term in lowered})


def analyse(text: str, module_id: int = 14) -> Dict[str, Any]:
    indicators = []
    for name, terms in _PATTERNS.items():
        found = _hits(text, terms)
        if found:
            indicators.append({
                "pattern": name,
                "matched_terms": found,
                "interpretation": _INTERPRETATIONS[name],
                "confidence": round(min(0.9, 0.3 + 0.12 * len(found)), 2),
            })
    return {
        "module_id": module_id,
        "indicators": indicators,
        "count": len(indicators),
        "caveat": _CAVEAT,
        "defensive_use_only": True,
        "note": "No manipulation content, targeting advice or psychological operation is produced.",
    }


def analyse_discussion(texts: List[str]) -> Dict[str, Any]:
    analyses = [analyse(text) for text in texts]
    repeated = []
    names = [{item["pattern"] for item in a["indicators"]} for a in analyses]
    for index in range(1, len(names)):
        shared = names[index - 1] & names[index]
        if shared:
            repeated.append({
                "index": index,
                "shared_patterns": sorted(shared),
                "interpretation": "possible repeated framing across messages",
            })
    return {
        "analyses": analyses,
        "repeated_patterns": repeated,
        "caveat": _CAVEAT,
        "note": "Coordination is not established by wording similarity alone.",
    }
