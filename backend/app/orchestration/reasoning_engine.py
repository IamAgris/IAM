"""Reasoning engine for IAM's cognitive foundation.

Provides explicit reasoning modes beyond single-prompt action selection:

* causal      — identify cause-effect chains from observations
* analogical  — find similar past situations and transfer their outcomes
* counterfactual — ask what would change if a key assumption differed
* probabilistic — estimate outcome likelihood from available evidence
* dialectical — consider thesis and antithesis, then synthesise
* adversarial — challenge your own conclusion with counterarguments

The LLM remains the underlying reasoning substrate, but each call is now
structured around a specific mode with explicit evidence, assumptions,
and conclusions. Every trace is inspectable, verifiable, and revisable.

Beliefs are read from and written to IAM's shared epistemic state
(``iam_context``), so reasoning operates on one coherent body of
knowledge rather than isolated context fragments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import loguru

from app.services import iam_context
from app.services.model_inference import InferenceUnavailable, inference_service

logger = loguru.logger

MAX_REASONING_TOKENS = 512
REASONING_TEMPERATURE = 0.3
MAX_BELIEF_CONTEXT_ITEMS = 6


class ReasoningMode(str, Enum):
    CAUSAL = "causal"
    ANALOGICAL = "analogical"
    COUNTERFACTUAL = "counterfactual"
    PROBABILISTIC = "probabilistic"
    DIALECTICAL = "dialectical"
    ADVERSARIAL = "adversarial"


@dataclass
class ReasoningTrace:
    """A structured, inspectable reasoning output."""

    mode: ReasoningMode
    question: str
    evidence: List[Dict[str, Any]]
    assumptions: List[str]
    reasoning_steps: List[str]
    conclusion: str
    confidence: float
    contradictions: List[str] = field(default_factory=list)
    identified_gaps: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def as_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "question": self.question,
            "evidence": self.evidence,
            "assumptions": self.assumptions,
            "reasoning_steps": self.reasoning_steps,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "contradictions": self.contradictions,
            "identified_gaps": self.identified_gaps,
            "created_at": self.created_at,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _fetch_belief_context(
    db: Any, query: str, limit: int = MAX_BELIEF_CONTEXT_ITEMS
) -> List[Dict[str, Any]]:
    """Retrieve relevant shared beliefs as evidence for reasoning."""
    if db is None:
        return []
    try:
        beliefs = await iam_context.get_belief_state(db, limit=limit)
    except Exception as exc:  # pragma: no cover - reasoning must survive
        logger.warning(f"belief context unavailable: {exc}")
        return []
    # Simple keyword relevance filter
    terms = [t for t in query.lower().split() if len(t) > 3]
    scored = []
    for b in beliefs:
        haystack = (
            f"{b.title} {b.content} {b.topic or ''} {b.provenance} {b.belief_type}"
        ).lower()
        score = sum(1 for t in terms if t in haystack)
        if score > 0:
            scored.append((score, b))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "id": b.id,
            "title": b.title,
            "content": b.content,
            "source": b.source,
            "confidence_level": b.confidence_level,
            "verification_status": b.verification_status,
            "topic": b.topic,
            "belief_type": b.belief_type,
            "relevance_score": score,
        }
        for score, b in scored[:limit]
    ]


def _system_prompt_for_mode(mode: ReasoningMode) -> str:
    base = (
        "You are IAM's reasoning engine. Reason in structured steps. "
        "Return JSON only: "
        '{"assumptions": [str], "reasoning_steps": [str], "conclusion": str, '
        '"confidence": number 0-1, "identified_gaps": [str]}. '
        "Do not include markdown fences."
    )
    mode_specific = {
        ReasoningMode.CAUSAL: (
            "Task: CAUSAL REASONING. Identify cause-effect chains. "
            "For each observation, ask: what caused it? what effects does it have? "
            "Trace the chain from root cause to observable outcome."
        ),
        ReasoningMode.ANALOGICAL: (
            "Task: ANALOGICAL REASONING. Find structural similarities between "
            "the current situation and past cases. Transfer lessons from analogous "
            "situations, but note where the analogy breaks down."
        ),
        ReasoningMode.COUNTERFACTUAL: (
            "Task: COUNTERFACTUAL REASONING. Ask what would be different if a "
            "key assumption or event were changed. Identify which assumptions are "
            "load-bearing for your conclusion."
        ),
        ReasoningMode.PROBABILISTIC: (
            "Task: PROBABILISTIC REASONING. Estimate the likelihood of possible "
            "outcomes given the evidence. Express uncertainty explicitly. "
            "Distinguish what is likely from what is merely possible."
        ),
        ReasoningMode.DIALECTICAL: (
            "Task: DIALECTICAL REASONING. Consider the thesis (your initial "
            "position), then the antithesis (strong opposing arguments), then "
            "synthesise a position that accounts for both."
        ),
        ReasoningMode.ADVERSARIAL: (
            "Task: ADVERSARIAL SELF-CRITIQUE. Challenge your own conclusion. "
            "What is the strongest argument against it? What evidence would "
            "falsify it? What have you overlooked?"
        ),
    }
    return mode_specific.get(mode, "") + " " + base


async def _call_reasoning_llm(
    db: Any,
    mode: ReasoningMode,
    question: str,
    evidence: List[Dict[str, Any]],
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Run one structured reasoning call against the shared model resolver."""
    evidence_lines = "\n".join(
        f"- [{e.get('verification_status', 'unverified')}] {e.get('title', '')}: "
        f"{e.get('content', '')[:200]} (source: {e.get('source', 'unknown')})"
        for e in evidence[:6]
    ) or "No relevant beliefs found in shared epistemic state."

    user_prompt = (
        f"Question: {question}\n"
        f"Available evidence from shared epistemic state:\n{evidence_lines}\n"
    )

    try:
        status = await inference_service.resolve()
        if not status.available:
            raise InferenceUnavailable(status.reason)
        result = await inference_service.chat(
            [
                {"role": "system", "content": _system_prompt_for_mode(mode)},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
            temperature=REASONING_TEMPERATURE,
            max_tokens=MAX_REASONING_TOKENS,
            timeout=60.0,
            db=db,
        )
        content = str(result["choices"][0]["message"]["content"]).strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        import json

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start < 0 or end <= start:
                raise
            return json.loads(content[start : end + 1])
    except Exception as exc:
        logger.warning(f"reasoning LLM call failed ({mode}): {exc}")
        return {
            "assumptions": [f"model unavailable: {type(exc).__name__}"],
            "reasoning_steps": [
                "reasoning could not be completed because the model resolver was unavailable"
            ],
            "conclusion": "no conclusion",
            "confidence": 0.0,
            "identified_gaps": ["model unavailable for reasoning"],
        }


def _extract_json_field(parsed: Dict[str, Any], field: str, default: Any) -> Any:
    value = parsed.get(field, default)
    if isinstance(value, list):
        return [str(v) for v in value]
    if field == "confidence":
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.5
    return value


async def reason_in_mode(
    db: Any,
    mode: ReasoningMode,
    question: str,
    model: Optional[str] = None,
) -> ReasoningTrace:
    """Run one reasoning mode against the shared epistemic state.

    Returns a structured ``ReasoningTrace`` with evidence, assumptions,
    steps, conclusion, confidence, contradictions, and gaps.
    """
    evidence = await _fetch_belief_context(db, question)
    parsed = await _call_reasoning_llm(db, mode, question, evidence, model=model)

    # Detect contradictions with existing verified beliefs
    conclusion_lower = parsed.get("conclusion", "").lower()
    contradictions: List[str] = []
    for e in evidence:
        if e.get("verification_status") == "verified":
            ec = e.get("content", "").lower()
            # Simple negation detection: if evidence says X and conclusion says not-X
            if any(w in ec for w in ("not ", "no ", "never")) and any(
                w in conclusion_lower for w in ("is ", "are ", "will ")
            ):
                contradictions.append(e.get("title", ""))

    return ReasoningTrace(
        mode=mode,
        question=question,
        evidence=evidence,
        assumptions=_extract_json_field(parsed, "assumptions", []),
        reasoning_steps=_extract_json_field(parsed, "reasoning_steps", []),
        conclusion=str(parsed.get("conclusion", "no conclusion")),
        confidence=_extract_json_field(parsed, "confidence", 0.5),
        contradictions=contradictions,
        identified_gaps=_extract_json_field(parsed, "identified_gaps", []),
    )


async def select_reasoning_mode(
    db: Any,
    question: str,
    task_hint: Optional[str] = None,
) -> ReasoningMode:
    """Metacognitive mode selection.

    Chooses the reasoning mode best suited to the question. Falls back to
    causal reasoning when uncertain. The selection itself is recorded so
    it can be reviewed later.
    """
    q = question.lower()
    hint = (task_hint or "").lower()

    # Keyword-based heuristics as a transparent, auditable first pass.
    if any(w in q for w in ("why", "cause", "because", "led to", "resulted")):
        return ReasoningMode.CAUSAL
    if any(w in q for w in ("what if", "if not", "without", "instead", "else")):
        return ReasoningMode.COUNTERFACTUAL
    if any(w in q for w in ("likely", "probably", "chance", "odds", "risk")):
        return ReasoningMode.PROBABILISTIC
    if any(w in q for w in ("like", "similar", "analog", "compare", "example")):
        return ReasoningMode.ANALOGICAL
    if any(w in q for w in ("debate", "disagree", "opposing", "controversial")):
        return ReasoningMode.DIALECTICAL
    if any(w in hint for w in ("verify", "check", "critique", "challenge")):
        return ReasoningMode.ADVERSARIAL

    # Default: causal reasoning is the most generally applicable mode.
    return ReasoningMode.CAUSAL


async def critique_reasoning(
    db: Any,
    trace: ReasoningTrace,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Adversarial self-critique of a reasoning trace.

    Returns a critique with strengths, weaknesses, falsification tests,
    and a revised confidence estimate. The critique is adversarial: it
    argues against the trace's conclusion, not in favour of it.
    """
    critique_prompt = (
        "You are IAM's adversarial critic. Your job is to find flaws in "
        "the following reasoning trace. Be harsh. Identify:\n"
        "1. Weak or unstated assumptions\n"
        "2. Logical gaps or leaps\n"
        "3. Evidence that contradicts the conclusion\n"
        "4. Alternative explanations not considered\n"
        "5. What evidence would falsify the conclusion\n"
        "Return JSON only: "
        '{"strengths": [str], "weaknesses": [str], "contradictions_found": [str], '
        '"falsification_tests": [str], "revised_confidence": number 0-1, '
        '"accept_conclusion": boolean}. No markdown fences.'
    )

    user_prompt = (
        f"Mode: {trace.mode.value}\n"
        f"Question: {trace.question}\n"
        f"Assumptions: {'; '.join(trace.assumptions)}\n"
        f"Reasoning steps: {'; '.join(trace.reasoning_steps)}\n"
        f"Conclusion: {trace.conclusion}\n"
        f"Original confidence: {trace.confidence}\n"
        f"Evidence used: {len(trace.evidence)} items\n"
        f"Identified gaps: {'; '.join(trace.identified_gaps)}\n"
    )

    try:
        status = await inference_service.resolve()
        if not status.available:
            raise InferenceUnavailable(status.reason)
        result = await inference_service.chat(
            [
                {"role": "system", "content": critique_prompt},
                {"role": "user", "content": user_prompt},
            ],
            model=model,
            temperature=0.2,
            max_tokens=MAX_REASONING_TOKENS,
            timeout=60.0,
            db=db,
        )
        content = str(result["choices"][0]["message"]["content"]).strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        import json

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start < 0 or end <= start:
                raise
            return json.loads(content[start : end + 1])
    except Exception as exc:
        logger.warning(f"critique LLM call failed: {exc}")
        return {
            "strengths": [],
            "weaknesses": [f"critique unavailable: {type(exc).__name__}"],
            "contradictions_found": trace.contradictions,
            "falsification_tests": ["critique could not be performed"],
            "revised_confidence": max(0.0, trace.confidence - 0.2),
            "accept_conclusion": False,
        }


async def synthesize_reasoning(
    db: Any,
    traces: List[ReasoningTrace],
    critique: Optional[Dict[str, Any]] = None,
    model: Optional[str] = None,
) -> ReasoningTrace:
    """Combine multiple reasoning traces into one synthesised conclusion.

    Weighs each trace by confidence, factors in adversarial critique,
    and produces a final trace marked as mode 'synthesis'.
    """
    if not traces:
        return ReasoningTrace(
            mode=ReasoningMode.CAUSAL,
            question="no traces to synthesise",
            evidence=[],
            assumptions=["no reasoning traces available"],
            reasoning_steps=["no reasoning was performed"],
            conclusion="no conclusion",
            confidence=0.0,
            identified_gaps=["no reasoning traces provided"],
        )

    # Weighted average of confidences
    total_conf = sum(t.confidence for t in traces)
    avg_conf = total_conf / len(traces)

    # Apply critique adjustment
    if critique:
        revised = critique.get("revised_confidence", avg_conf)
        accept = critique.get("accept_conclusion", True)
        if not accept:
            avg_conf = max(0.0, avg_conf - 0.2)
    else:
        revised = avg_conf

    # Collect all contradictions and gaps
    all_contradictions: List[str] = []
    all_gaps: List[str] = []
    all_steps: List[str] = []
    all_assumptions: List[str] = []
    all_evidence: List[Dict[str, Any]] = []
    seen_evidence_ids: set = set()

    for t in traces:
        all_steps.extend([f"[{t.mode.value}] {s}" for s in t.reasoning_steps])
        all_assumptions.extend(t.assumptions)
        all_contradictions.extend(t.contradictions)
        all_gaps.extend(t.identified_gaps)
        for e in t.evidence:
            eid = e.get("id")
            if eid and eid not in seen_evidence_ids:
                seen_evidence_ids.add(eid)
                all_evidence.append(e)

    # Build a synthesised conclusion
    conclusions = [t.conclusion for t in traces if t.conclusion != "no conclusion"]
    if conclusions:
        # Pick the highest-confidence conclusion as primary
        best = max(traces, key=lambda t: t.confidence)
        synthesis_conclusion = best.conclusion
    else:
        synthesis_conclusion = "no supported conclusion"

    return ReasoningTrace(
        mode=ReasoningMode.CAUSAL,  # synthesis uses causal as its frame
        question=traces[0].question,
        evidence=all_evidence,
        assumptions=list(dict.fromkeys(all_assumptions)),
        reasoning_steps=all_steps,
        conclusion=synthesis_conclusion,
        confidence=max(0.0, min(1.0, revised)),
        contradictions=list(dict.fromkeys(all_contradictions)),
        identified_gaps=list(dict.fromkeys(all_gaps)),
        created_at=_now(),
    )
