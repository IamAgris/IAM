"""Document 26 (OD-45): module registry and Phase 2 analysis framework.

Modules 1–4 (Division 1) are functional in this increment. Every other module
returns a structured A8 refusal until implemented and validated. No module
produces a profile of an identifiable person.
"""

import re
from typing import Any, Dict, List, Optional

_TOKEN = re.compile(r"[a-z]{4,}")

MODULE_REGISTRY: Dict[int, Dict[str, str]] = {
    1: {"division": "D1", "name": "Psychology Intelligence"},
    2: {"division": "D1", "name": "Personality Intelligence"},
    3: {"division": "D1", "name": "Emotional Intelligence"},
    4: {"division": "D1", "name": "Cognitive Intelligence"},
    24: {"division": "D1", "name": "Human Evolution Intelligence"},
    25: {"division": "D1", "name": "Developmental Psychology Intelligence"},
    5: {"division": "D2", "name": "Motivation Intelligence"},
    6: {"division": "D2", "name": "Decision Intelligence"},
    7: {"division": "D2", "name": "Habit and Learning Intelligence"},
    29: {"division": "D2", "name": "Economic Behaviour Intelligence"},
    30: {"division": "D2", "name": "Crisis Behaviour Intelligence"},
    34: {"division": "D2", "name": "Information Behaviour Intelligence"},
    8: {"division": "D3", "name": "Communication Intelligence"},
    9: {"division": "D3", "name": "Interpersonal Intelligence"},
    10: {"division": "D3", "name": "Social Dynamics Intelligence"},
    31: {"division": "D3", "name": "Leadership Psychology Intelligence"},
    32: {"division": "D3", "name": "Trust and Reputation Intelligence"},
    37: {"division": "D3", "name": "Conflict Resolution Intelligence"},
    11: {"division": "D4", "name": "Group Behaviour Intelligence"},
    12: {"division": "D4", "name": "Crowd and Society Intelligence"},
    26: {"division": "D4", "name": "Cross-Cultural Intelligence"},
    28: {"division": "D4", "name": "Geopolitical Behaviour Intelligence"},
    33: {"division": "D4", "name": "Collective Intelligence"},
    35: {"division": "D4", "name": "Technological Adaptation Intelligence"},
    36: {"division": "D4", "name": "Intergenerational Intelligence"},
    38: {"division": "D4", "name": "Behavioural Resilience Intelligence"},
    16: {"division": "D5", "name": "Historical Research Intelligence"},
    17: {"division": "D5", "name": "Historical Behaviour Analysis"},
    18: {"division": "D5", "name": "Historical Psychology Intelligence"},
    19: {"division": "D5", "name": "Historical Social Dynamics"},
    20: {"division": "D5", "name": "Historical Decision Intelligence"},
    21: {"division": "D5", "name": "Historical Conflict and Cooperation"},
    22: {"division": "D5", "name": "Historical Patterns and Trends"},
    23: {"division": "D5", "name": "Historical Forecasting Intelligence"},
    27: {"division": "D5", "name": "Historical Civilisation Intelligence"},
    13: {"division": "D6", "name": "Behavioural Forecasting"},
    14: {"division": "D6", "name": "Psychological Threat and Manipulation Intelligence"},
    15: {"division": "D6", "name": "Behavioural Learning and Evaluation"},
}

IMPLEMENTED = {
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20,
    21, 22, 23, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38,
}

MODULE_CUES = {
    1: {"psychology", "theory", "behaviour", "behavioural"},
    2: {"personality", "trait", "individual difference", "temperament"},
    3: {"emotion", "fear", "anger", "affect", "mood"},
    4: {"memory", "belief", "bias", "reasoning", "perception"},
    5: {"need", "incentive", "goal", "value", "motivation", "reward"},
    6: {"decision", "choice", "risk", "uncertainty", "trade-off"},
    7: {"habit", "routine", "reinforcement", "repeated", "adaptation"},
    29: {"economic", "price", "income", "cost", "market", "incentive"},
    30: {"crisis", "disaster", "emergency", "shock", "uncertainty"},
    34: {"information", "misinformation", "news", "share", "message", "source"},
    8: {"language", "tone", "rhetoric", "message", "communication", "framing"},
    9: {"relationship", "trust", "boundary", "cooperation", "conflict", "dyad"},
    10: {"norm", "influence", "network", "peer", "social", "contagion"},
    11: {"group", "conformity", "leadership", "team", "collective decision"},
    12: {"crowd", "public", "society", "population", "trend", "societal"},
    26: {"culture", "cultural", "cross-cultural", "region", "tradition"},
    28: {"nation", "state", "institution", "geopolitical", "diplomacy", "government"},
    31: {"leader", "leadership", "authority", "command", "decision"},
    32: {"trust", "reputation", "credibility", "integrity", "trust repair"},
    33: {"knowledge sharing", "collective intelligence", "crowdsource", "deliberation"},
    35: {"technology", "adoption", "digital", "automation", "innovation"},
    36: {"generation", "generational", "cohort", "intergenerational", "ageing"},
    37: {"escalation", "de-escalation", "negotiation", "resolution", "reconciliation"},
    38: {"resilience", "adversity", "adaptation", "coping", "recovery"},
    13: {"forecast", "possible outcome", "probability", "scenario", "future"},
    14: {"manipulation", "coercion", "propaganda", "deception", "threat"},
    16: {"historical source", "archive", "document", "chronicle"},
    17: {"historical behaviour", "period", "century", "past response"},
    18: {"historical motivation", "historical fear", "belief", "leader psychology"},
    19: {"civilisation", "society", "institution", "hierarchy", "migration"},
    20: {"decision", "alternative", "consequence", "contemporaneous"},
    21: {"war", "conflict", "alliance", "diplomacy", "reconciliation"},
    22: {"recurring pattern", "historical trend", "longue duree", "cycle"},
    23: {"precedent", "analogy", "historical lesson", "comparison"},
    27: {"civilisation", "decline", "development", "institutional trust", "inequality"},
}
_CAVEAT = "Interpretations are possibilities, not psychological diagnoses or facts about a person."


def list_modules() -> Dict[str, Any]:
    return {
        "count": len(MODULE_REGISTRY),
        "implemented": sorted(IMPLEMENTED),
        "modules": [{"id": mid, **info} for mid, info in sorted(MODULE_REGISTRY.items())],
    }


def analyse(module_id: int, question: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    info = MODULE_REGISTRY.get(module_id)
    if info is None:
        return {"error": "UNKNOWN_MODULE", "module_id": module_id}
    if module_id == 14:
        from app.services.hbi.manipulation import analyse as detect_manipulation
        detection = detect_manipulation(question)
        return {
            "module_id": 14,
            "name": info["name"],
            "division": info["division"],
            "status": "implemented",
            "indicators": detection["indicators"],
            "count": detection["count"],
            "caveat": detection["caveat"],
            "defensive_use_only": True,
            "note": "Pattern recognition only; no influence content or targeting guidance.",
        }
    if module_id not in IMPLEMENTED:
        return {
            "module_id": module_id,
            "name": info["name"],
            "status": "not_implemented",
            "refusal": {
                "code": "A8_CAPABILITY_NOT_VALIDATED",
                "reason": "module_not_yet_implemented_or_validated",
                "what_would_change": ["module implementation", "functional tests", "calibration evidence"],
            },
        }

    tokens = set(_TOKEN.findall(question.lower()))
    cues = MODULE_CUES.get(module_id, set())
    matched = []
    for record in records:
        claim = record["claim"].lower()
        score = (2 if module_id in (record.get("module_ids") or []) else 0)
        score += sum(1 for token in tokens if token in claim)
        score += sum(1 for cue in cues if cue in claim)
        if score > 0:
            matched.append((score, record))
    matched.sort(key=lambda item: item[0], reverse=True)
    matched = [record for _, record in matched]
    refusal = None
    if not matched:
        refusal = {
            "code": "INSUFFICIENT_EVIDENCE",
            "reason": "no_graded_records_for_this_module_and_question",
            "what_would_change": ["licensed research ingestion", "module-specific evidence"],
        }
    return {
        "module_id": module_id,
        "name": info["name"],
        "division": info["division"],
        "status": "implemented" if matched else "no_evidence",
        "epistemic_objects": [
            {
                "record_ref": r["record_ref"],
                "claim": r["claim"],
                "evidence_class": r["evidence_class"],
                "confidence": r["confidence"],
                "alternatives": r.get("alternatives", []),
                "causal_status": r.get("causal_status", "correlational"),
            }
            for r in matched
        ],
        "confidence": round(sum(r["confidence"] for r in matched) / len(matched), 2) if matched else 0.0,
        "caveat": _CAVEAT,
        "refusal": refusal,
    }
