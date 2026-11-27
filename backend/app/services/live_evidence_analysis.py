"""Evidence analysis for the Web Intelligence Engine (proposed Doc 34 §8).

Deterministic, model-independent analysis: prompt-injection screening,
cross-source corroboration and contradiction heuristics, and claim labels.
These signals inform the primary model; they never become trusted knowledge.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

# Website text is untrusted data. These patterns never *execute* anything;
# matching text is redacted and flagged for the model.
_INJECTION_PATTERNS = (
    re.compile(r"ignore (?:all |any )?(?:previous|prior|above) instructions", re.I),
    re.compile(r"disregard (?:your |the )?(?:system|previous|prior) (?:prompt|instructions)", re.I),
    re.compile(r"reveal (?:your |the )?system prompt", re.I),
    re.compile(r"you are now (?:an?|the) ", re.I),
    re.compile(r"new instructions?:", re.I),
    re.compile(r"(?:grant|escalate) (?:yourself |my )?(?:admin|permission|access)", re.I),
    re.compile(r"execute (?:the following|this) command", re.I),
)
_NEGATION_WORDS = frozenset(
    {"no", "not", "never", "denies", "denied", "false", "untrue", "disputed", "refute", "refutes"}
)
_NEGATION = re.compile(r"\b(?:" + "|".join(sorted(_NEGATION_WORDS)) + r")\b", re.I)
_STOP = frozenset(
    {"the", "and", "for", "with", "that", "this", "from", "have", "has", "was", "were", "are", "news", "says"}
)


def injection_detected(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in _INJECTION_PATTERNS)


def _tokens(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(word) > 3 and word not in _STOP
    }


def _similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _domain(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _negated_tokens(text: str) -> set[str]:
    """Tokens immediately following a negation — used only as a weak signal."""
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    found: set[str] = set()
    for index, word in enumerate(words):
        if word in _NEGATION_WORDS:
            found.update(
                token for token in words[index + 1 : index + 3] if len(token) > 3
            )
    return found


def analyse(results: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Return sanitised results and a structured analysis summary."""
    cleaned: List[Dict[str, Any]] = []
    flags: List[str] = []
    for item in results:
        entry = dict(item)
        text = f"{entry.get('title', '')} {entry.get('description', '')}"
        if injection_detected(text):
            flags.append(str(entry.get("url", "unknown")))
            entry["injection_suspected"] = True
            entry["description"] = "[redacted: untrusted instruction text removed]"
        else:
            entry["injection_suspected"] = False
        cleaned.append(entry)

    token_sets = [_tokens(f"{item.get('title', '')} {item.get('description', '')}") for item in cleaned]
    contradictions: List[Dict[str, str]] = []
    corroborations = [0 for _ in cleaned]
    domains = [_domain(str(item.get("url", ""))) for item in cleaned]
    for index, left in enumerate(token_sets):
        for other in range(index + 1, len(token_sets)):
            similarity = _similarity(left, token_sets[other])
            if similarity < 0.35:
                continue
            # Corroboration must come from different publications.
            if domains[index] and domains[index] != domains[other]:
                corroborations[index] += 1
                corroborations[other] += 1
            left_text = f"{cleaned[index].get('title', '')} {cleaned[index].get('description', '')}"
            right_text = f"{cleaned[other].get('title', '')} {cleaned[other].get('description', '')}"
            left_negated = _negated_tokens(left_text)
            right_negated = _negated_tokens(right_text)
            contradiction = (
                similarity >= 0.5
                and (
                    (left_negated and left_negated & token_sets[other] and not right_negated)
                    or (right_negated and right_negated & left and not left_negated)
                )
            )
            if contradiction:
                contradictions.append(
                    {
                        "left": str(cleaned[index].get("url", "")),
                        "right": str(cleaned[other].get("url", "")),
                    }
                )

    contradictory_urls = {
        url for pair in contradictions for url in (pair["left"], pair["right"])
    }
    confidences: List[float] = []
    for index, item in enumerate(cleaned):
        url = str(item.get("url", ""))
        if url in contradictory_urls:
            label = "conflicting"
            confidence = 0.25
        elif item.get("injection_suspected"):
            label = "unverified"
            confidence = 0.20
        elif corroborations[index] >= 2:
            label = "corroborated"
            confidence = 0.85
        elif corroborations[index] == 1:
            label = "corroborated"
            confidence = 0.70
        else:
            label = "single_source"
            confidence = 0.45
        item["claim_label"] = label
        item["confidence"] = round(confidence, 2)
        item["corroboration_count"] = corroborations[index]
        confidences.append(confidence)

    summary = {
        "claim_labels": [str(item["claim_label"]) for item in cleaned],
        "corroboration_count": sum(corroborations),
        "contradictions": contradictions,
        "injection_flags": flags,
        "mean_confidence": round(sum(confidences) / len(confidences), 2) if confidences else 0.0,
    }
    return cleaned, summary
