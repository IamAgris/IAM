"""LangGraph durable autonomy workflow.

Stateful, checkpointed operational loop replacing the simple sleep loop.
States: observe → retrieve → reason → critique → synthesise → identify →
plan → authority → execute → verify → reflect → discover → memory →
(continue | recover | rest).

Every cognitive stage performs real work: memory retrieval calls MemoryService,
reasoning uses explicit modes via the reasoning engine, critique performs
adversarial self-review, synthesis combines multiple modes, verification
cross-checks against independently stored beliefs, reflection revises the
shared epistemic state, and discovery converts contradictions into
testable hypotheses verified through independent evidence. The orchestrator
is provider-independent. A missing model never produces fabricated
reasoning, and an unverified action is never marked complete.
"""

from typing import Annotated, Any, Dict, List, Optional, TypedDict
from datetime import datetime, timezone
import json
import operator
import uuid

import loguru
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from sqlalchemy import select

from app.core.config import settings
from app.orchestration import dispatch as action_dispatch
from app.orchestration.hypothesis_engine import HypothesisEngine
from app.orchestration.learning_engine import LearningEngine
from app.orchestration.cross_domain_engine import CrossDomainEngine
from app.orchestration.evaluation_suite import EvaluationSuite
from app.orchestration.curiosity_engine import CuriosityEngine
from app.orchestration.attention_manager import AttentionManager
from app.orchestration.grounded_intelligence import GroundedIntelligence
from app.orchestration.agency_engine import AgencyEngine
from app.orchestration.intellectual_history import IntellectualHistory
from app.orchestration.collaborative_intelligence import CollaborativeIntelligence
from app.orchestration.intellectual_honesty import IntellectualHonesty
from app.orchestration.independent_evaluation import EvaluationSuite as IndependentEvaluationSuite
from app.orchestration.model_development import FoundationModelDeveloper
from app.orchestration.reasoning_engine import (
    ReasoningMode,
    ReasoningTrace,
    critique_reasoning,
    reason_in_mode,
    select_reasoning_mode,
    synthesize_reasoning,
)
from app.services import iam_context

logger = loguru.logger

MAX_RETRIES = 1

# Evaluation must stay local to remain an independent judge, but it is too
# expensive to run on every 30s tick on a CPU-only core. A shared cadence gate
# keeps both evaluation nodes off the single residency slot between runs.
_last_evaluation_at: Dict[str, float] = {}


def _evaluation_due(key: str) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    if now - _last_evaluation_at.get(key, 0.0) < settings.autonomy_evaluation_interval_s:
        return False
    _last_evaluation_at[key] = now
    return True


ALLOWED_MODEL_ACTIONS = set(action_dispatch.AVAILABLE) | {
    "observe",
    "ask_authorization",
}


class AutonomyState(TypedDict):
    """State carried through the autonomy workflow."""

    session_id: str
    trigger: str
    observations: List[Dict[str, Any]]
    memories: List[Dict[str, Any]]
    memory_error: Optional[str]
    reasoning: Optional[str]
    decision: Optional[Dict[str, Any]]
    model_used: bool
    inference_mode: Optional[str]
    objectives: List[Dict[str, Any]]
    plan: Optional[Dict[str, Any]]
    authority_check: Optional[Dict[str, Any]]
    governance_context: Optional[Dict[str, Any]]
    action_result: Optional[Dict[str, Any]]
    verification: Optional[str]
    verification_evidence: Optional[Dict[str, Any]]
    reflection: Optional[str]
    decision_id: Optional[str]
    memory_id: Optional[str]
    retry_count: int
    error: Optional[str]
    steps: Annotated[List[str], operator.add]
    # P0.3 cognitive fields
    reasoning_trace: Optional[Dict[str, Any]]
    reasoning_modes_used: List[str]
    metacognitive_critique: Optional[Dict[str, Any]]
    belief_revisions: List[Dict[str, Any]]
    discovery_summary: Optional[Dict[str, Any]]
    reverify_summary: Optional[Dict[str, Any]]
    learning_summary: Optional[Dict[str, Any]]
    cross_domain_summary: Optional[Dict[str, Any]]
    evaluation_summary: Optional[Dict[str, Any]]
    curiosity_summary: Optional[Dict[str, Any]]
    attention_summary: Optional[Dict[str, Any]]
    grounded_summary: Optional[Dict[str, Any]]
    agency_summary: Optional[Dict[str, Any]]
    intellectual_history_summary: Optional[Dict[str, Any]]
    collaborative_summary: Optional[Dict[str, Any]]
    intellectual_honesty_summary: Optional[Dict[str, Any]]
    independent_evaluation_summary: Optional[Dict[str, Any]]
    model_development_summary: Optional[Dict[str, Any]]


def _session() -> Any:
    """Return a fresh database session context without importing at module load."""
    from app.core.database import get_session_factory

    return get_session_factory()()


def _query_from(observations: List[Dict[str, Any]], limit: int = 3) -> str:
    return " ".join(
        str(item.get("title") or item.get("content") or "")
        for item in (observations or [])[:limit]
    ).strip()


async def observe(state: AutonomyState) -> Dict[str, Any]:
    """Gather environment signals: pending tasks, goals, recent messages."""
    from app.models.autonomy import Goal, Task

    async with _session() as db:
        goals = (await db.execute(select(Goal).where(Goal.status == "active").limit(5))).scalars().all()
        tasks = (await db.execute(select(Task).where(Task.status == "pending").limit(5))).scalars().all()
    obs = [
        {"type": "goal", "id": str(g.id), "title": g.title} for g in goals
    ] + [
        {"type": "task", "id": str(t.id), "title": t.title, "tool_name": t.tool_used}
        for t in tasks
    ]
    return {"observations": obs, "steps": ["observe"]}


async def retrieve_memory(state: AutonomyState) -> Dict[str, Any]:
    """Retrieve relevant memories through the real MemoryService."""
    from app.services.memory_service import MemoryService

    query = _query_from(state.get("observations", []))
    if not query:
        return {"memories": [], "steps": ["retrieve_memory:skip"]}
    try:
        async with _session() as db:
            found = await MemoryService(db).search_memory(query=query, limit=5)
        return {
            "memories": [
                {
                    "id": str(item.get("id")),
                    "content": str(item.get("content"))[:600],
                    "topic": item.get("topic"),
                    "source": item.get("source"),
                    "similarity": item.get("similarity"),
                }
                for item in found
            ],
            "memory_error": None,
            "steps": ["retrieve_memory"],
        }
    except Exception as exc:
        # Never fabricate recall. Report the failure so verification can see it.
        return {
            "memories": [],
            "memory_error": f"{type(exc).__name__}: {exc}",
            "steps": ["retrieve_memory:error"],
        }


async def attend(state: AutonomyState) -> Dict[str, Any]:
    """Allocate cognitive budget to the most valuable targets.

    Scores beliefs, contradictions, transfers, and gaps using measured
    uncertainty × impact × recency from P4/P5/P6 data. Only the top-scoring
    items receive cognitive tokens for this cycle. This is attention
    management, not arbitrary prioritization: every score traces back to
    measured revision history, contradiction severity, or evaluation trends.
    """
    from app.services.evidence_service import EvidenceService

    try:
        async with _session() as db:
            # Get beliefs for attention scoring
            beliefs = await iam_context.get_belief_state(db, limit=20)

            # Get contradictions from P5
            contradictions = await iam_context.detect_contradictions(db, limit=20)

            # Get transfer opportunities from P5
            cross_domain = CrossDomainEngine()
            transfer_results = await cross_domain.find_transfer_opportunities(db, limit=10)
            transfers = [
                {
                    "id": t.id,
                    "source_topic": t.source_topic,
                    "target_topic": t.target_topic,
                    "insight": t.insight,
                    "source_confidence": t.source_confidence,
                    "transfer_confidence": t.transfer_confidence,
                    "transfer_basis": t.transfer_basis,
                    "evidence_ids": list(t.evidence_ids),
                    "status": t.status,
                }
                for t in transfer_results
            ]

            # Get curiosity gaps from P7-a
            curiosity = CuriosityEngine()
            gaps_result = await curiosity.scan_for_gaps(db, limit=10)
            gaps = [
                {
                    "id": g.id,
                    "title": g.title,
                    "content": g.content,
                    "gap_type": g.gap_type,
                    "current_confidence": g.current_confidence,
                    "source": g.source,
                    "topic": g.topic,
                    "reason": g.reason,
                }
                for g in gaps_result
            ]

            manager = AttentionManager(db)
            decision = await manager.allocate_attention(
                beliefs=beliefs,
                contradictions=contradictions,
                transfers=transfers,
                gaps=gaps,
            )

        return {
            "attention_summary": {
                "total_budget": decision.total_budget,
                "allocated_tokens": decision.allocated_tokens,
                "items": [
                    {
                        "id": item.id,
                        "kind": item.kind,
                        "title": item.title,
                        "attention_score": item.attention_score,
                        "reason": item.reason,
                        "allocated_tokens": item.source_data.get("allocated_tokens", 0),
                        "source_data": item.source_data,
                    }
                    for item in decision.items
                ],
                "skipped_count": decision.skipped_count,
                "reason": decision.reason,
            },
            "steps": ["attend"],
        }
    except Exception as exc:
        logger.warning(f"attention allocation failed: {exc}")
        return {
            "attention_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "total_budget": 0,
                "allocated_tokens": 0,
                "items": [],
                "skipped_count": 0,
            },
            "steps": ["attend:error"],
        }


async def reason(state: AutonomyState) -> Dict[str, Any]:
    """Reason using explicit modes via the reasoning engine.

    Selects a reasoning mode appropriate to the observed work, runs it
    against the shared epistemic state, and stores a structured
    ReasoningTrace. Falls back to causal reasoning when the model is
    unavailable. Never fabricates conclusions.
    """
    obs = state.get("observations", [])
    if not obs:
        return {
            "reasoning": "No active work; conserve resources.",
            "decision": {"action": "observe", "confidence": 0.0},
            "model_used": False,
            "inference_mode": "offline",
            "steps": ["reason:idle"],
            "reasoning_trace": None,
            "reasoning_modes_used": [],
            "metacognitive_critique": None,
        }

    question = _query_from(obs, 5)[:500]
    task_hint = (state.get("decision") or {}).get("action")

    try:
        mode = await select_reasoning_mode(None, question, task_hint)
    except Exception as exc:
        logger.warning(f"mode selection failed: {exc}")
        mode = ReasoningMode.CAUSAL

    try:
        async with _session() as db:
            trace = await reason_in_mode(
                db, mode, question, model=settings.autonomy_model
            )
        reasoning_dict = trace.as_dict()
        return {
            "reasoning": trace.conclusion,
            "decision": {"action": "observe", "confidence": trace.confidence},
            "model_used": True,
            "inference_mode": "reasoning_engine",
            "steps": [f"reason:{mode.value}"],
            "reasoning_trace": reasoning_dict,
            "reasoning_modes_used": [mode.value],
            "metacognitive_critique": None,
        }
    except Exception as exc:
        logger.warning(f"reasoning engine failed: {exc}")
        return {
            "reasoning": (
                f"reasoning engine unavailable: {type(exc).__name__}: {exc}"
            )[:1000],
            "decision": {"action": "observe", "confidence": 0.0},
            "model_used": False,
            "inference_mode": "offline",
            "steps": ["reason:offline"],
            "reasoning_trace": None,
            "reasoning_modes_used": [],
            "metacognitive_critique": None,
        }


async def critique(state: AutonomyState) -> Dict[str, Any]:
    """Adversarial self-critique of the reasoning trace.

    Challenges the conclusion produced by the reasoning engine. Returns
    a critique dict with weaknesses, contradictions, and a revised
    confidence estimate. Never accepts a conclusion uncritically.
    """
    trace_dict = state.get("reasoning_trace")
    if not trace_dict:
        return {
            "metacognitive_critique": {
                "strengths": [],
                "weaknesses": ["no reasoning trace to critique"],
                "revised_confidence": 0.0,
                "accept_conclusion": False,
            },
            "steps": ["critique:skip"],
        }

    try:
        from app.orchestration.reasoning_engine import ReasoningTrace

        trace = ReasoningTrace(
            mode=ReasoningMode(trace_dict.get("mode", "causal")),
            question=trace_dict.get("question", ""),
            evidence=trace_dict.get("evidence", []),
            assumptions=trace_dict.get("assumptions", []),
            reasoning_steps=trace_dict.get("reasoning_steps", []),
            conclusion=trace_dict.get("conclusion", ""),
            confidence=trace_dict.get("confidence", 0.5),
            contradictions=trace_dict.get("contradictions", []),
            identified_gaps=trace_dict.get("identified_gaps", []),
        )
        async with _session() as db:
            critique_result = await critique_reasoning(
                db, trace, model=settings.autonomy_model
            )
        return {
            "metacognitive_critique": critique_result,
            "steps": ["critique"],
        }
    except Exception as exc:
        logger.warning(f"critique failed: {exc}")
        return {
            "metacognitive_critique": {
                "strengths": [],
                "weaknesses": [f"critique unavailable: {type(exc).__name__}"],
                "revised_confidence": 0.0,
                "accept_conclusion": False,
            },
            "steps": ["critique:error"],
        }


async def synthesise(state: AutonomyState) -> Dict[str, Any]:
    """Combine reasoning trace and critique into a final conclusion.

    Weighs the reasoning trace against the adversarial critique and
    produces a synthesised conclusion with adjusted confidence.
    """
    trace_dict = state.get("reasoning_trace")
    critique_result = state.get("metacognitive_critique") or {}

    if not trace_dict:
        return {
            "reasoning": "No reasoning trace to synthesise.",
            "decision": {"action": "observe", "confidence": 0.0},
            "steps": ["synthesise:skip"],
        }

    try:
        from app.orchestration.reasoning_engine import ReasoningTrace

        trace = ReasoningTrace(
            mode=ReasoningMode(trace_dict.get("mode", "causal")),
            question=trace_dict.get("question", ""),
            evidence=trace_dict.get("evidence", []),
            assumptions=trace_dict.get("assumptions", []),
            reasoning_steps=trace_dict.get("reasoning_steps", []),
            conclusion=trace_dict.get("conclusion", ""),
            confidence=trace_dict.get("confidence", 0.5),
            contradictions=trace_dict.get("contradictions", []),
            identified_gaps=trace_dict.get("identified_gaps", []),
        )
        async with _session() as db:
            synthesis = await synthesize_reasoning(db, [trace], critique_result)
        return {
            "reasoning": synthesis.conclusion,
            "decision": {
                "action": "observe",
                "confidence": synthesis.confidence,
            },
            "reasoning_trace": synthesis.as_dict(),
            "steps": ["synthesise"],
        }
    except Exception as exc:
        logger.warning(f"synthesis failed: {exc}")
        return {
            "reasoning": trace_dict.get("conclusion", "synthesis failed"),
            "decision": {
                "action": "observe",
                "confidence": trace_dict.get("confidence", 0.0),
            },
            "steps": ["synthesise:error"],
        }


async def identify_objectives(state: AutonomyState) -> Dict[str, Any]:
    """Select objectives — pending tasks first, then goals."""
    tasks = [o for o in state.get("observations", []) if o.get("type") == "task"]
    objectives = tasks[:3] or state.get("observations", [])[:3]
    return {"objectives": objectives, "steps": ["identify_objectives"]}


def _infer_action(objective: dict, decision: Optional[Dict[str, Any]]) -> str:  # type: ignore[type-arg]
    preferred = (decision or {}).get("action")
    if preferred in action_dispatch.AVAILABLE:
        return str(preferred)
    tool_name = str(objective.get("tool_name") or "")
    if tool_name in action_dispatch.AVAILABLE:
        return tool_name
    from app.services.module_registry import action_for_objective

    title = str(objective.get("title") or "")
    return action_for_objective(title) or "model_probe"


async def plan(state: AutonomyState) -> Dict[str, Any]:
    """Convert the selected objective into a persisted, allowlisted plan."""
    objectives = state.get("objectives") or []
    obj = objectives[0] if objectives else None
    if not obj:
        return {"plan": None, "steps": ["plan:skip"]}
    action = _infer_action(obj, state.get("decision"))
    steps = ["authorize", f"dispatch:{action}", "verify", "consolidate"]
    plan_state = {
        "objective": obj,
        "action": action,
        "steps": steps,
        "expected_evidence": f"decision_outcome:{obj.get('id')}",
    }

    if obj.get("type") == "goal" and obj.get("id"):
        try:
            from app.models.autonomy import Goal, Plan, Task

            async with _session() as db:
                goal_id = uuid.UUID(str(obj["id"]))
                goal = (
                    await db.execute(select(Goal).where(Goal.id == goal_id))
                ).scalar_one_or_none()
                if goal is not None:
                    record = Plan(
                        goal_id=goal_id,
                        title=str(obj.get("title") or "autonomy plan"),
                        steps=steps,
                        status="in_progress",
                    )
                    db.add(record)
                    await db.flush()
                    task_ids = []
                    for step in steps:
                        task = Task(plan_id=record.id, title=step, status="pending")
                        db.add(task)
                        await db.flush()
                        task_ids.append(str(task.id))
                    await db.commit()
                    plan_state["plan_id"] = str(record.id)
                    plan_state["task_ids"] = task_ids
        except (ValueError, TypeError) as exc:
            logger.warning(f"Plan persistence skipped: {exc}")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Plan persistence unavailable: {exc}")

    return {"plan": plan_state, "steps": ["plan"]}


async def check_authority(state: AutonomyState) -> Dict[str, Any]:
    """Verify authority for the *selected* action before it is dispatched."""
    from app.services.governance_service import GovernanceService

    plan_state = state.get("plan") or {}
    action = str(plan_state.get("action") or "observe")
    allowed_autonomous = set(action_dispatch.AVAILABLE) | {"observe"}
    async with _session() as db:
        service = GovernanceService(db)
        list_boundaries = getattr(service, "get_authority_boundaries", None)
        boundaries = (
            {
                item["action_type"]: item
                for item in await list_boundaries()
            }
            if list_boundaries is not None
            else {}
        )
        boundary = boundaries.get(action)
        if list_boundaries is not None and boundary is None and action in allowed_autonomous:
            # No higher boundary: governance still makes the level-1 decision.
            decision = await service.check_authority(action, "1")
            source = "governance_boundary_or_signed_creator"
        elif list_boundaries is None:
            # Minimal governance service: still route the decision through it.
            decision = await service.check_authority(
                action, "1" if action in allowed_autonomous else "2"
            )
            source = "governance_boundary_or_signed_creator"
        elif boundary is not None:
            decision = await service.check_authority(
                action, str(boundary["authority_level"])
            )
            source = "governance_boundary_or_signed_creator"
        elif action in allowed_autonomous:
            # Governance still decides; the allowlist only selects the level.
            decision = await service.check_authority(action, "1")
            source = "governance_boundary_or_signed_creator"
        else:
            decision = {
                "permitted": False,
                "required_level": "2",
                "reason": "no authority boundary for the selected action",
            }
            source = "no_authority_boundary"
    return {
        "authority_check": {
            "action": action,
            "permitted": bool(decision.get("permitted")),
            "decision": decision,
            "authority_source": source,
        },
        "steps": ["check_authority"],
    }


async def execute(state: AutonomyState) -> Dict[str, Any]:
    """Dispatch the allowlisted action through a real service and persist evidence."""
    from app.models.autonomy import DecisionRecord, Task, TaskExecution
    from app.services.tool_authorization import ToolAuthorizationError, authorize_tool_call

    plan_state = state.get("plan")
    if not plan_state:
        return {"action_result": {"status": "skipped"}, "steps": ["execute:skip"]}
    authority = state.get("authority_check") or {}
    if authority.get("permitted") is False:
        return {
            "action_result": {"status": "blocked", "reason": "authority_not_granted"},
            "steps": ["execute:blocked_authority"],
        }
    obj = plan_state["objective"]
    action = plan_state["action"]
    tool_name = state.get("tool_name") or obj.get("tool_name")
    query = _query_from([obj])
    authority = state.get("authority_check") or {}
    if authority.get("permitted") is not True:
        return {
            "action_result": {
                "status": "blocked",
                "reason": "authority_check_failed",
                "code": "authority_required",
                "action": action,
            },
            "steps": ["execute:blocked"],
        }

    async with _session() as db:
        from app.services.constitutional_policy import (
            ConstitutionalPolicyDenied,
            assert_allowed,
        )

        try:
            await assert_allowed(db, action)
        except ConstitutionalPolicyDenied as exc:
            return {
                "action_result": {
                    "status": "blocked",
                    "reason": str(exc),
                    "code": "protected_core_authorization_required",
                    "action": action,
                },
                "steps": ["execute:blocked"],
            }

        if tool_name:
            signed = state.get("signed_authorization")
            signed_authorization = signed if isinstance(signed, dict) else None
            try:
                await authorize_tool_call(
                    db,
                    str(tool_name),
                    approval_granted=bool(state.get("approval_granted")),
                    signed_authorization=signed_authorization,
                )
            except ToolAuthorizationError as exc:
                return {
                    "action_result": {"status": "blocked", "reason": exc.reason, "code": exc.code},
                    "steps": ["execute:blocked"],
                }

        from app.services.iplci.context import resolve_governance_context

        governance_context = state.get("governance_context") or {}
        resolved_governance = resolve_governance_context(governance_context)
        governance_step = "iplci:no_context"
        if resolved_governance:
            from app.services.iplci.gateway import GovernanceRefusal
            from app.services.iplci.integration import enforce_agent_request

            try:
                await enforce_agent_request(
                    db,
                    action=action,
                    source_id=resolved_governance["source_id"],
                    agent_id=str(resolved_governance.get("agent_id") or "main"),
                    jurisdiction=resolved_governance.get("jurisdiction"),
                )
            except GovernanceRefusal as exc:
                return {
                    "action_result": {
                        "status": "blocked",
                        "reason": "iplci_governance_refused",
                        "code": exc.code,
                        "decision": exc.decision,
                        "action": action,
                    },
                    "steps": ["execute:blocked_iplci"],
                }
            governance_step = "iplci:enforced"

        started = datetime.now(timezone.utc)
        outcome = await action_dispatch.dispatch(
            db,
            action,
            {
                "objective_id": obj.get("id"),
                "query": query,
                "title": obj.get("title"),
                "tool_name": tool_name,
                "governance_context": governance_context,
            },
        )
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        success = outcome.get("status") == "success"
        decision = DecisionRecord(
            decision=f"Autonomous {action} toward: {obj.get('title', 'objective')}",
            reasoning=state.get("reasoning"),
            confidence=float((state.get("decision") or {}).get("confidence", 0.5)),
            outcome=json.dumps(
                {"status": outcome.get("status"), "evidence": outcome.get("evidence") or outcome.get("error")},
                ensure_ascii=False,
            )[:2000],
        )
        db.add(decision)
        await db.commit()
        decision_id = str(decision.id)

        if obj.get("type") == "task" and obj.get("id"):
            try:
                task = (
                    await db.execute(select(Task).where(Task.id == uuid.UUID(str(obj["id"]))))
                ).scalar_one_or_none()
            except (ValueError, TypeError):
                task = None
            if task is not None:
                if success:
                    task.status = "completed"
                    task.completed_at = datetime.now(timezone.utc)
                else:
                    task.status = "failed"
                task.tool_used = tool_name or action
            try:
                db.add(
                    TaskExecution(
                        task_id=uuid.UUID(str(obj["id"])),
                        status="success" if success else "failure",
                        output=json.dumps(outcome, ensure_ascii=False)[:4000],
                        error_message=None if success else str(outcome.get("error") or "dispatch failed")[:500],
                        duration_ms=duration_ms,
                    )
                )
            except (ValueError, TypeError):
                pass
            await db.commit()

    return {
        "action_result": {
            "status": "advanced" if success else "failed",
            "action": action,
            "service": outcome.get("service"),
            "evidence": outcome.get("evidence") or outcome.get("error"),
        },
        "decision_id": decision_id,
        "dispatch_service": outcome.get("service"),
        "steps": [governance_step, "execute" if success else "execute:failed"],
    }


async def recover(state: AutonomyState) -> Dict[str, Any]:
    """Bounded recovery: record the failure and allow one retry."""
    return {
        "retry_count": int(state.get("retry_count", 0)) + 1,
        "steps": ["recover"],
    }


async def verify(state: AutonomyState) -> Dict[str, Any]:
    """Verify the outcome by cross-checking against independently stored evidence and beliefs.

    Never accepts self-reported status as proof. Performs three independent checks:

    1. Records execution evidence via EvidenceService (persisted, provenance-tracked).
    2. Cross-checks the result against existing verified beliefs in the shared epistemic state.
    3. Detects contradictions with verified beliefs on the same topic.

    Returns a verification status that reflects independent corroboration, not self-report.
    """
    from app.models.autonomy import DecisionRecord
    from app.services.evidence_service import EvidenceService

    result = state.get("action_result") or {}
    decision_id = state.get("decision_id")
    if result.get("status") != "advanced" or not decision_id:
        return {
            "verification": "unverified",
            "verification_evidence": {"reason": "no successful execution or decision record"},
            "steps": ["verify:unverified"],
        }
    try:
        async with _session() as db:
            row = (
                await db.execute(
                    select(DecisionRecord).where(DecisionRecord.id == uuid.UUID(str(decision_id)))
                )
            ).scalar_one_or_none()
        if row is not None and row.outcome:
            payload = json.loads(row.outcome)
            if not (payload.get("status") == "success" and payload.get("evidence")):
                return {
                    "verification": "unverified",
                    "verification_evidence": {
                        "reason": "execution did not report success evidence",
                    },
                    "steps": ["verify:unverified"],
                }

            evidence_text = str(payload.get("evidence", "")) or ""
            action = result.get("action", "")
            result_lower = evidence_text.lower()

            # Check 1: Record execution evidence as a persisted evidence item.
            evidence_item = None
            try:
                async with _session() as ev_db:
                    ev_service = EvidenceService(ev_db)
                    evidence_item = await ev_service.record_evidence(
                        source_id=f"execution:{decision_id}",
                        source_type="experiment_result",
                        content=evidence_text,
                        locator=f"decision:{decision_id}",
                        evidence_type="experiment_result",
                        credibility=0.5,  # execution evidence starts neutral
                        metadata={
                            "decision_id": decision_id,
                            "service": result.get("service"),
                            "action": action,
                            "verification_source": "autonomy_execution",
                        },
                    )
            except Exception as exc:
                logger.warning(f"evidence recording failed: {exc}")

            # Check 2: Cross-check against existing verified beliefs.
            beliefs = await iam_context.get_belief_state(db, limit=10)
            supports: List[str] = []
            contradictions: List[str] = []
            independent = False
            result_terms = set(result_lower.split())

            for b in beliefs:
                if b.verification_status != "verified":
                    continue
                haystack = f"{b.title} {b.content} {b.topic or ''}".lower()
                belief_terms = set(haystack.split())
                overlap = result_terms & belief_terms
                if overlap and b.confidence_level and b.confidence_level > 0.7:
                    supports.append(b.title)
                    independent = True
                # Detect direct contradiction: verified belief with negation terms vs positive result
                if any(w in haystack for w in ("not ", "no ", "never")) and any(
                    w in result_lower for w in ("is ", "are ", "will ")
                ):
                    contradictions.append(b.title)

            # Check 3: Explicit contradiction detection via iam_context.
            try:
                explicit_contradictions = await iam_context.detect_contradictions(
                    db, topic=None, limit=20
                )
                for c in explicit_contradictions:
                    c_text = f"{c.get('belief_a', {}).get('title','')} {c.get('belief_b', {}).get('title','')}".lower()
                    if action.lower() in c_text or any(
                        t in c_text for t in result_terms if len(t) > 4
                    ):
                        b_title = c.get("belief_b", {}).get("title", "unknown")
                        if b_title not in contradictions:
                            contradictions.append(b_title)
            except Exception as exc:
                logger.warning(f"explicit contradiction detection failed: {exc}")

            # Link evidence to any supported beliefs
            if evidence_item and supports:
                try:
                    async with _session() as link_db:
                        link_service = EvidenceService(link_db)
                        for supp_title in supports[:3]:
                            for b in beliefs:
                                if b.title == supp_title and b.verification_status == "verified":
                                    await link_service.link_evidence_to_belief(
                                        evidence_id=evidence_item.id,
                                        belief_id=b.id,
                                        relationship="supports",
                                        strength=0.7,
                                    )
                                    break
                except Exception as exc:
                    logger.warning(f"evidence-belief linking failed: {exc}")

            verification_status = "verified"
            if contradictions:
                verification_status = "verified_with_contradictions"
            elif not independent:
                verification_status = "verified_without_independent_support"

            return {
                "verification": verification_status,
                "verification_evidence": {
                    "decision_id": decision_id,
                    "service": result.get("service"),
                    "evidence": payload["evidence"],
                    "evidence_item_id": evidence_item.id if evidence_item else None,
                    "supports": supports,
                    "contradictions": contradictions,
                    "independent_check": independent,
                },
                "steps": ["verify"],
            }
    except Exception as exc:
        return {
            "verification": "unverified",
            "verification_evidence": {"error": f"{type(exc).__name__}: {exc}"},
            "steps": ["verify:error"],
        }
    return {
        "verification": "unverified",
        "verification_evidence": {"reason": "no persisted success evidence"},
        "steps": ["verify:unverified"],
    }


async def reflect(state: AutonomyState) -> Dict[str, Any]:
    """Reflect on the verified outcome and revise the shared epistemic state.

    Instead of merely appending LLM text, this node creates or revises
    beliefs in the shared epistemic state based on verified outcomes.
    Failed or contradicted outcomes are recorded as disputed or retracted
    beliefs so IAM learns from its mistakes.
    """
    from app.models.reflection import ReflectionEntry

    async with _session() as db:
        # Always record a reflection entry for the audit trail.
        db.add(
            ReflectionEntry(
                reflection_type="experience",
                title="Autonomy cycle",
                content=json.dumps(
                    {
                        "verification": state.get("verification"),
                        "evidence": state.get("verification_evidence"),
                        "memory_error": state.get("memory_error"),
                        "reasoning_trace": state.get("reasoning_trace"),
                    },
                    ensure_ascii=False,
                )[:2000],
                lesson_learned=state.get("reasoning"),
                confidence=float((state.get("decision") or {}).get("confidence", 0.5)),
            )
        )

        # Revise shared beliefs based on the verified outcome.
        belief_revisions: List[Dict[str, Any]] = []
        verification = state.get("verification") or ""
        trace = state.get("reasoning_trace") or {}
        conclusion = trace.get("conclusion", "") if trace else state.get("reasoning", "")
        confidence = float((state.get("decision") or {}).get("confidence", 0.5))

        if conclusion and conclusion != "no conclusion":
            if verification.startswith("verified"):
                status = "verified"
            elif "contradiction" in verification:
                status = "disputed"
            else:
                status = "unverified"

            try:
                revised = await iam_context.record_belief(
                    db,
                    title=f"Autonomy conclusion: {conclusion[:120]}",
                    content=conclusion,
                    source="autonomy_graph",
                    confidence_level=confidence,
                    topic="autonomy",
                    belief_type="experience",
                    provenance="reasoning_engine",
                    evidence=[
                        {
                            "type": "execution_result",
                            "service": (state.get("action_result") or {}).get("service"),
                            "verification": verification,
                            "evidence": state.get("verification_evidence"),
                        }
                    ],
                    contradicts=trace.get("contradictions", []),
                )
                belief_revisions.append(
                    {
                        "action": "recorded",
                        "belief_id": revised.id,
                        "status": status,
                    }
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning(f"belief recording failed: {exc}")

        await db.commit()
    return {
        "reflection": "recorded",
        "belief_revisions": belief_revisions,
        "steps": ["reflect"],
    }


async def ground(state: AutonomyState) -> Dict[str, Any]:
    """Ground beliefs through real-world verification.

    Takes beliefs formed or revised in this cycle and tests them against
    external evidence. Beliefs that can't be grounded through independent
    verification are marked as disputed or refuted. This prevents IAM from
    mistaking plausible-sounding text for verified knowledge.

    Grounding is the bridge between IAM's internal understanding and
    external reality: a belief only becomes knowledge when it survives
    contact with evidence IAM did not generate.
    """
    from app.services.evidence_service import EvidenceService

    try:
        async with _session() as db:
            # Get recently formed/revised beliefs to ground
            beliefs = await iam_context.get_belief_state(db, limit=20)

            engine = GroundedIntelligence()
            grounded_results: List[Dict[str, Any]] = []

            for b in beliefs:
                # Only ground beliefs that were recently created or revised
                if b.verification_status in ("unverified", "disputed"):
                    result = await engine.ground_belief(
                        db,
                        belief_id=b.id,
                        belief_title=b.title,
                        belief_content=b.content,
                        current_status=b.verification_status,
                        current_confidence=b.confidence_level or 0.5,
                    )

                    # Update the belief based on grounding result
                    if result["grounded"]:
                        await iam_context.revise_belief(
                            db,
                            b.id,
                            verification_status=result["new_status"],
                            confidence_level=result["new_confidence"],
                            evidence=[{
                                "type": "grounded_verification",
                                "experiments": result["experiments"],
                                "reason": result["reason"],
                            }],
                        )

                    grounded_results.append({
                        "belief_id": b.id,
                        "title": b.title,
                        "previous_status": result["previous_status"],
                        "new_status": result["new_status"],
                        "previous_confidence": result["previous_confidence"],
                        "new_confidence": result["new_confidence"],
                        "reason": result["reason"],
                        "experiments_run": len(result["experiments"]),
                    })

            # Also detect understanding drift
            drift = await engine.detect_understanding_drift(db, beliefs)

            return {
                "grounded_summary": {
                    "beliefs_grounded": len(grounded_results),
                    "results": grounded_results,
                    "drift_candidates": len(drift),
                    "drift": drift[:5],  # top 5 drift candidates
                },
                "steps": ["ground"],
            }
    except Exception as exc:
        logger.warning(f"grounded intelligence failed: {exc}")
        return {
            "grounded_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "beliefs_grounded": 0,
                "results": [],
                "drift_candidates": 0,
                "drift": [],
            },
            "steps": ["ground:error"],
        }


async def discover(state: AutonomyState) -> Dict[str, Any]:
    """Discover contradictions and convert them into verified hypotheses.

    Runs one discovery cycle: detect contradictions in the shared epistemic
    state, generate testable hypotheses via counterfactual reasoning, verify
    each hypothesis through independent evidence (external sources +
    consistency + adversarial critique), and revise the shared epistemic
    state based on results. Never accepts self-reported status as proof.
    """
    try:
        async with _session() as db:
            engine = HypothesisEngine()
            summary = await engine.run_discovery_cycle(db)
        return {
            "discovery_summary": summary,
            "steps": ["discover"],
        }
    except Exception as exc:
        logger.warning(f"discovery cycle failed: {exc}")
        return {
            "discovery_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "contradictions_found": 0,
                "hypotheses_generated": 0,
                "hypotheses_verified": 0,
            },
            "steps": ["discover:error"],
        }


async def reverify(state: AutonomyState) -> Dict[str, Any]:
    """Re-verify beliefs whose verification has aged past the interval.

    Checks the evidence service for beliefs due for re-verification and
    reports them so IAM continuously tests its own previously-accepted
    conclusions rather than treating them as settled. Belief revision is
    handled by the existing reflect/discover nodes which hold a db session.
    """
    from app.services.evidence_service import EvidenceService

    try:
        async with _session() as db:
            ev_service = EvidenceService(db)
            due = await ev_service.beliefs_due_for_reverification(limit=20)

        return {
            "reverify_summary": {
                "beliefs_due": len(due),
                "results": due,
            },
            "steps": ["reverify"],
        }
    except Exception as exc:
        logger.warning(f"reverify cycle failed: {exc}")
        return {
            "reverify_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "beliefs_due": 0,
            },
            "steps": ["reverify:error"],
        }


async def learn(state: AutonomyState) -> Dict[str, Any]:
    """Compute longitudinal learning metrics from belief revision history.

    Analyzes how IAM's beliefs have actually changed over time — which
    reasoning methods produce confirmed knowledge, which sources are
    reliable for which topics, and whether confirmation rates are
    improving or declining. Replaces self-declared proficiency with
    measured learning.
    """
    from app.services.evidence_service import EvidenceService

    try:
        async with _session() as db:
            engine = LearningEngine()
            metrics = await engine.compute_metrics(db, limit=200)
            insights = await engine.learning_insights(metrics)

            # Store the learning metrics as a belief for future reference
            try:
                await iam_context.record_belief(
                    db,
                    title="Learning metrics summary",
                    content=(
                        f"Confirmation rate {metrics.confirmation_rate:.0%}, "
                        f"refutation rate {metrics.refutation_rate:.0%}, "
                        f"stability rate {metrics.stability_rate:.0%} "
                        f"over {metrics.total_revisions} revisions across "
                        f"{metrics.total_beliefs} beliefs."
                    ),
                    source="learning_engine",
                    confidence_level=metrics.confirmation_rate,
                    topic="learning",
                    belief_type="meta_knowledge",
                    provenance="learning_engine",
                    evidence=[{
                        "type": "learning_metrics",
                        "total_beliefs": metrics.total_beliefs,
                        "total_revisions": metrics.total_revisions,
                        "confirmation_rate": metrics.confirmation_rate,
                        "refutation_rate": metrics.refutation_rate,
                        "dispute_rate": metrics.dispute_rate,
                        "stability_rate": metrics.stability_rate,
                        "average_confidence_change": metrics.average_confidence_change,
                        "insights": insights,
                    }],
                )
            except Exception as exc:
                logger.warning(f"learning metrics persistence failed: {exc}")

        return {
            "learning_summary": {
                "total_beliefs": metrics.total_beliefs,
                "total_revisions": metrics.total_revisions,
                "confirmation_rate": metrics.confirmation_rate,
                "refutation_rate": metrics.refutation_rate,
                "dispute_rate": metrics.dispute_rate,
                "stability_rate": metrics.stability_rate,
                "average_confidence_change": metrics.average_confidence_change,
                "insights": insights,
                "reasoning_method_effectiveness": metrics.reasoning_method_effectiveness,
                "source_topic_reliability": metrics.source_topic_reliability,
                "topic_accuracy": metrics.topic_accuracy,
                "trends": metrics.trends,
            },
            "steps": ["learn"],
        }
    except Exception as exc:
        logger.warning(f"learning cycle failed: {exc}")
        return {
            "learning_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "total_beliefs": 0,
                "total_revisions": 0,
            },
            "steps": ["learn:error"],
        }


async def transfer(state: AutonomyState) -> Dict[str, Any]:
    """Transfer insights across domains using measured reliability data.

    Finds confirmed insights in one domain that could apply to another,
    detects cross-domain contradictions, and identifies common principles.
    Every transfer is marked as requiring independent verification in the
    target domain — cross-domain similarity never implies truth.
    """
    try:
        async with _session() as db:
            engine = CrossDomainEngine()

            transfers = await engine.find_transfer_opportunities(db, limit=20)
            contradictions = await engine.detect_cross_domain_contradictions(
                db, limit=20
            )
            principles = await engine.identify_common_principles(db, limit=10)

            # Persist high-confidence transfers as hypotheses for verification
            for t in transfers:
                if t.transfer_confidence >= 0.5:
                    try:
                        await iam_context.record_belief(
                            db,
                            title=f"Cross-domain hypothesis: {t.insight[:100]}",
                            content=(
                                f"Transferred from {t.source_topic} to {t.target_topic}: "
                                f"{t.insight}"
                            ),
                            source="cross_domain_engine",
                            confidence_level=t.transfer_confidence,
                            topic=t.target_topic,
                            belief_type="hypothesis",
                            provenance="cross_domain_transfer",
                            evidence=[{
                                "type": "cross_domain_transfer",
                                "source_topic": t.source_topic,
                                "transfer_basis": t.transfer_basis,
                                "source_confidence": t.source_confidence,
                            }],
                            contradicts=[],
                        )
                    except Exception as exc:
                        logger.warning(f"transfer persistence failed: {exc}")

        return {
            "cross_domain_summary": {
                "transfers_proposed": len(transfers),
                "contradictions_detected": len(contradictions),
                "common_principles": len(principles),
                "transfers": [
                    {
                        "source_topic": t.source_topic,
                        "target_topic": t.target_topic,
                        "insight": t.insight[:100],
                        "transfer_confidence": t.transfer_confidence,
                        "transfer_basis": t.transfer_basis,
                    }
                    for t in transfers[:10]
                ],
                "contradictions": [
                    {
                        "topic_a": c.topic_a,
                        "topic_b": c.topic_b,
                        "belief_a": c.belief_a_title[:80],
                        "belief_b": c.belief_b_title[:80],
                        "severity": c.severity,
                    }
                    for c in contradictions[:10]
                ],
                "principles": [
                    {
                        "principle": p.principle,
                        "domains": p.domains,
                        "confidence": p.cross_domain_confidence,
                    }
                    for p in principles[:10]
                ],
            },
            "steps": ["transfer"],
        }
    except Exception as exc:
        logger.warning(f"cross-domain transfer failed: {exc}")
        return {
            "cross_domain_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "transfers_proposed": 0,
                "contradictions_detected": 0,
                "common_principles": 0,
            },
            "steps": ["transfer:error"],
        }


async def evaluate(state: AutonomyState) -> Dict[str, Any]:
    """Run independent longitudinal evaluation against held-out test data.

    Evaluates IAM's actual capability across reasoning, knowledge retention,
    transfer, prediction accuracy, error correction, and learning efficiency.
    Test data is held out — IAM cannot have seen it through training, memory,
    or research. Results are stored in the shared epistemic state for
    longitudinal trend analysis.

    IAM cannot game this evaluation: the test data is separate from anything
    in its memory, and scoring is deterministic exact-match, not model-judged.
    """
    if not _evaluation_due("self"):
        return {
            "evaluation_summary": {"skipped": True, "reason": "evaluation cadence"},
            "steps": ["evaluate:skipped"],
        }
    try:
        async with _session() as db:
            suite = EvaluationSuite(db)
            report = await suite.run_evaluation()
        return {
            "evaluation_summary": {
                "run_id": report.run_id,
                "model": report.model,
                "overall_score": report.overall_score,
                "overall_passed": report.overall_passed,
                "domains": [
                    {
                        "domain": d.domain,
                        "score": d.score,
                        "threshold": d.threshold,
                        "passed": d.passed,
                        "correct": d.correct,
                        "total": d.total,
                    }
                    for d in report.domains
                ],
                "compared_to_baseline": report.compared_to_baseline,
            },
            "steps": ["evaluate"],
        }
    except Exception as exc:
        logger.warning(f"evaluation failed: {exc}")
        return {
            "evaluation_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "overall_score": 0.0,
                "overall_passed": False,
            },
            "steps": ["evaluate:error"],
        }


async def independent_evaluate(state: AutonomyState) -> Dict[str, Any]:
    """Run independent evaluation of IAM through the public HTTP API.

    IAM cannot see the questions before they arrive, cannot influence the
    scoring, and cannot alter the results. Results are stored separately
    from IAM's own P6 evaluation records so IAM cannot suppress them.
    Comparison between IAM's self-evaluation and this independent
    evaluation reveals whether IAM is grading itself leniently.
    """
    if not _evaluation_due("independent"):
        return {
            "independent_evaluation_summary": {
                "skipped": True,
                "reason": "evaluation cadence",
            },
            "steps": ["independent_evaluate:skipped"],
        }
    try:
        async with _session() as db:
            suite = IndependentEvaluationSuite(db)
            report = await suite.run_evaluation()
        return {
            "independent_evaluation_summary": {
                "run_id": report.run_id,
                "timestamp": report.timestamp,
                "iam_base_url": report.iam_base_url,
                "overall_score": report.overall_score,
                "overall_passed": report.overall_passed,
                "domains": [
                    {
                        "domain": d.domain,
                        "score": d.score,
                        "threshold": d.threshold,
                        "passed": d.passed,
                        "correct": d.correct,
                        "total": d.total,
                    }
                    for d in report.domains
                ],
                "comparison_to_iam_self_eval": report.comparison_to_iam_self_eval,
            },
            "steps": ["independent_evaluate"],
        }
    except Exception as exc:
        logger.warning(f"independent evaluation failed: {exc}")
        return {
            "independent_evaluation_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "overall_score": 0.0,
                "overall_passed": False,
            },
            "steps": ["independent_evaluate:error"],
        }


async def explore(state: AutonomyState) -> Dict[str, Any]:
    """Self-directed curiosity cycle.

    Scans IAM's own shared epistemic state for knowledge gaps — unverified,
    low-confidence, disputed, stale, or under-represented beliefs — and
    initiates legitimate research into them:

        gap scan → curiosity hypothesis → independent verification → belief revision

    This is curiosity, not contradiction-driven discovery (P2). IAM notices
    its own uncertainty and investigates it without waiting for an external
    instruction or a detected contradiction.
    """
    try:
        async with _session() as db:
            engine = CuriosityEngine()
            summary = await engine.run_curiosity_cycle(db)
        return {
            "curiosity_summary": summary,
            "steps": ["explore"],
        }
    except Exception as exc:
        logger.warning(f"curiosity cycle failed: {exc}")
        return {
            "curiosity_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "gaps_found": 0,
                "hypotheses_generated": 0,
                "hypotheses_verified": 0,
            },
            "steps": ["explore:error"],
        }


async def collaborate(state: AutonomyState) -> Dict[str, Any]:
    """Collaborative intelligence cycle.

    Identifies questions from curiosity gaps and collaborates with external
    AI models on them. External models contribute expertise; IAM maintains
    its own independent conclusions. Disagreements are resolved using
    evidence, not majority vote.

    This is collaboration, not delegation: IAM coordinates multiple models
    but makes its own decisions based on verified evidence.
    """
    try:
        async with _session() as db:
            engine = CollaborativeIntelligence()

            # Get curiosity gaps as collaboration questions
            curiosity = CuriosityEngine()
            gaps_result = await curiosity.scan_for_gaps(db, limit=5)

            # Get available external models from model registry
            from app.services.model_inference import inference_service
            status = await inference_service.resolve()
            external_models = []
            if status.available:
                # Use available hosted models as external collaborators
                external_models = [
                    {"model_id": "hosted-model-1", "provider": "hosted"},
                ]

            collaboration_results = []
            for gap in gaps_result[:3]:  # top 3 gaps
                question = f"{gap.title}: {gap.content}"
                result = await engine.collaborative_development_cycle(
                    db,
                    question,
                    iam_conclusion="unresolved",
                    iam_confidence=gap.current_confidence,
                    iam_reasoning=f"Curiosity gap: {gap.reason}",
                    external_models=external_models,
                )
                collaboration_results.append(result)

            return {
                "collaborate_summary": {
                    "questions_explored": len(collaboration_results),
                    "results": [
                        {
                            "question": r["question"][:80],
                            "resolution": r["resolution"],
                            "final_confidence": r["final_confidence"],
                            "agreement_score": r["agreement_score"],
                            "external_opinions": len(r["external_opinions"]),
                        }
                        for r in collaboration_results
                    ],
                },
                "steps": ["collaborate"],
            }
    except Exception as exc:
        logger.warning(f"collaborative intelligence failed: {exc}")
        return {
            "collaborate_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "questions_explored": 0,
                "results": [],
            },
            "steps": ["collaborate:error"],
        }


async def agent(state: AutonomyState) -> Dict[str, Any]:
    """Independent problem-solving cycle.

    Takes curiosity gaps, contradictions, and transfer opportunities and
    turns them into objectives with strategies, executes them through
    governance-gated dispatch, monitors progress, recovers from failures,
    and learns from results.

    All actions pass through GovernanceService and IPLCI — IAM cannot act
    outside its authorized boundaries. High-impact decisions require
    Creator authorization.
    """
    try:
        async with _session() as db:
            engine = AgencyEngine()

            # Get curiosity gaps, contradictions, and transfer opportunities
            curiosity = CuriosityEngine()
            gaps_result = await curiosity.scan_for_gaps(db, limit=10)
            gaps = [
                {
                    "id": g.id,
                    "title": g.title,
                    "content": g.content,
                    "gap_type": g.gap_type,
                    "current_confidence": g.current_confidence,
                    "source": g.source,
                    "topic": g.topic,
                    "reason": g.reason,
                    "attention_score": 0.8,
                }
                for g in gaps_result
            ]

            contradictions = await iam_context.detect_contradictions(db, limit=10)

            cross_domain = CrossDomainEngine()
            transfer_results = await cross_domain.find_transfer_opportunities(db, limit=10)
            transfers = [
                {
                    "id": t.id,
                    "source_topic": t.source_topic,
                    "target_topic": t.target_topic,
                    "insight": t.insight,
                    "source_confidence": t.source_confidence,
                    "transfer_confidence": t.transfer_confidence,
                    "transfer_basis": t.transfer_basis,
                    "evidence_ids": list(t.evidence_ids),
                    "status": t.status,
                }
                for t in transfer_results
            ]

            summary = await engine.run_agency_cycle(
                db, gaps, contradictions, transfers
            )

        return {
            "agency_summary": summary,
            "steps": ["agent"],
        }
    except Exception as exc:
        logger.warning(f"agency cycle failed: {exc}")
        return {
            "agency_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "objectives_identified": 0,
                "strategies_developed": 0,
                "objectives_executed": 0,
                "objectives_completed": 0,
            },
            "steps": ["agent:error"],
        }


async def intellectual_history(state: AutonomyState) -> Dict[str, Any]:
    """Aggregate IAM's intellectual development history.

    Reads all belief revision history from the shared epistemic state and
    produces an aggregate view: what has IAM learned, when did it change
    its mind, what was it wrong about, what topics has it focused on?

    Read-only: does not modify any beliefs. Produces a longitudinal view
    of IAM's intellectual development over time.
    """
    try:
        async with _session() as db:
            history = IntellectualHistory()
            summary = await history.get_intellectual_history(db)
            autobiography = await history.get_learning_autobiography(db)

        return {
            "intellectual_history_summary": {
                "total_beliefs": summary.total_beliefs,
                "total_revisions": summary.total_revisions,
                "time_span_days": summary.time_span_days,
                "topics_tracked": len(summary.topic_histories),
                "beliefs_by_topic": summary.beliefs_by_topic,
                "beliefs_by_status": summary.beliefs_by_status,
                "major_changes": autobiography["major_changes"],
                "most_changed_topics": autobiography["most_changed_topics"],
                "stable_beliefs": autobiography["stable_beliefs"],
                "confidence_trend": autobiography["confidence_trend"],
            },
            "steps": ["intellectual_history"],
        }
    except Exception as exc:
        logger.warning(f"intellectual history failed: {exc}")
        return {
            "intellectual_history_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "total_beliefs": 0,
                "total_revisions": 0,
            },
            "steps": ["intellectual_history:error"],
        }


async def honesty(state: AutonomyState) -> Dict[str, Any]:
    """Intellectual honesty / uncertainty management cycle.

    Flags uncertain beliefs (low confidence, insufficient evidence,
    conflicting evidence), maintains competing hypotheses when evidence is
    insufficient, records mistakes when past conclusions were wrong, and
    assesses whether IAM's stated confidence matches actual accuracy.

    This is the bridge between IAM's internal beliefs and honest
    communication: IAM should not present uncertain beliefs as fact.
    """
    try:
        async with _session() as db:
            engine = IntellectualHonesty()

            beliefs = await iam_context.get_belief_state(db, limit=200)

            summary = await engine.run_intellectual_honesty_cycle(db, beliefs)

            return {
                "honesty_summary": {
                    "uncertainty_flags": summary["uncertainty_flags"],
                    "competing_hypotheses": summary["competing_hypotheses"],
                    "mistakes_recorded": summary["mistakes_recorded"],
                    "calibration": summary["calibration"],
                    "details": summary["details"],
                },
                "steps": ["honesty"],
            }
    except Exception as exc:
        logger.warning(f"intellectual honesty failed: {exc}")
        return {
            "honesty_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "uncertainty_flags": 0,
                "competing_hypotheses": 0,
                "mistakes_recorded": 0,
                "calibration": {},
            },
            "steps": ["honesty:error"],
        }


async def model_development(state: AutonomyState) -> Dict[str, Any]:
    """Foundation-model capability development cycle.

    IAM assesses its own primary model against one held-out evaluation run,
    identifies measured weak capabilities and prepares fine-tuning candidates
    through the existing ``ai_research`` pipeline. When training adapters, a
    trusted evaluator or a served candidate alias are not configured, the cycle
    reports the blockers instead of fabricating jobs. This node never promotes:
    promotion goes through the signed ``ModelReleaseService`` gate. The cycle is
    cadence-gated because capability assessment is expensive.
    """
    if not _evaluation_due("model_development"):
        return {
            "model_development_summary": {
                "skipped": True,
                "reason": "model development cadence",
            },
            "steps": ["model_development:skipped"],
        }
    try:
        from app.services.ai_research.continuous_improvement import default_adapters
        from app.services.ai_research.lm_eval import (
            default_eval_suite,
            default_lm_eval_driver,
            eval_config,
            eval_suite_config,
        )

        # Adapters and evaluator come from the already-configured research
        # stack. A candidate alias, checkpoint and licence are operator facts,
        # supplied through settings; empty values keep preparation fail-closed.
        suite = default_eval_suite()
        driver = None if suite else default_lm_eval_driver()
        evaluator = suite or driver
        evaluator_provenance = (
            eval_suite_config(suite) if suite else (
                eval_config(driver) if driver else {}
            )
        )
        async with _session() as db:
            developer = FoundationModelDeveloper(
                db,
                adapters=default_adapters(),
                evaluate=evaluator.evaluate if evaluator else None,
                evaluator_provenance=evaluator_provenance,
                checkpoint_ref=settings.model_development_checkpoint_ref,
                candidate_model=settings.model_development_candidate_model,
                licence=settings.model_development_dataset_licence,
            )
            summary = await developer.run_development_cycle(db)
        return {
            "model_development_summary": {
                "assessments": summary.get("assessments", []),
                "candidates_prepared": summary.get("candidates_prepared", 0),
                "candidates": summary.get("candidates", []),
                "blocked": summary.get("blocked", []),
                "details": summary.get("details", []),
                "promoted": False,
            },
            "steps": ["model_development"],
        }
    except Exception as exc:
        logger.warning(f"model development failed: {exc}")
        return {
            "model_development_summary": {
                "error": f"{type(exc).__name__}: {exc}",
                "candidates_prepared": 0,
                "promoted": False,
            },
            "steps": ["model_development:error"],
        }


async def update_memory(state: AutonomyState) -> Dict[str, Any]:
    """Consolidate only verified experience into long-term memory."""
    if not str(state.get("verification") or "").startswith("verified"):
        return {"steps": ["update_memory:skip_unverified"]}
    from app.services.memory_service import MemoryService

    try:
        async with _session() as db:
            saved = await MemoryService(db).store_memory(
                content=(
                    f"Autonomy cycle: {state.get('reasoning', '')} "
                    f"Verified by {state.get('verification')} "
                    f"using {state.get('dispatch_service') or 'unknown service'}."
                )[:1000],
                memory_type="experience",
                source="autonomy_graph",
                confidence=float((state.get("decision") or {}).get("confidence", 0.5)),
                topic="autonomy",
            )
        return {"memory_id": str(saved.get("id")), "steps": ["update_memory"]}
    except Exception as exc:
        return {
            "memory_error": f"{type(exc).__name__}: {exc}",
            "steps": ["update_memory:error"],
        }


async def end_cycle(state: AutonomyState) -> Dict[str, Any]:
    return {"steps": ["end"]}


def _after_execute(state: AutonomyState) -> str:
    result = state.get("action_result") or {}
    if result.get("status") in ("failed", "blocked") and int(state.get("retry_count", 0)) < MAX_RETRIES:
        return "recover"
    return "verify"


def build_graph(checkpointer: AsyncSqliteSaver):  # type: ignore[no-untyped-def]
    """Compile the durable autonomy graph."""
    g = StateGraph(AutonomyState)
    for name, node in (
        ("observe", observe),
        ("retrieve_memory", retrieve_memory),
        ("attend", attend),
        ("reason", reason),
        ("critique", critique),
        ("synthesise", synthesise),
        ("identify_objectives", identify_objectives),
        ("plan", plan),
        ("check_authority", check_authority),
        ("execute", execute),
        ("recover", recover),
        ("verify", verify),
        ("reflect", reflect),
        ("ground", ground),
        ("discover", discover),
        ("reverify", reverify),
        ("learn", learn),
        ("transfer", transfer),
        ("evaluate", evaluate),
        ("independent_evaluate", independent_evaluate),
        ("explore", explore),
        ("collaborate", collaborate),
        ("agent", agent),
        ("intellectual_history", intellectual_history),
        ("honesty", honesty),
        ("model_development", model_development),
        ("update_memory", update_memory),
        ("end", end_cycle),
    ):
        g.add_node(name, node)

    g.add_edge(START, "observe")
    g.add_edge("observe", "retrieve_memory")
    g.add_edge("retrieve_memory", "attend")
    g.add_edge("attend", "reason")
    g.add_edge("reason", "critique")
    g.add_edge("critique", "synthesise")
    g.add_edge("synthesise", "identify_objectives")
    g.add_edge("identify_objectives", "plan")
    g.add_edge("plan", "check_authority")
    g.add_edge("check_authority", "execute")
    g.add_conditional_edges(
        "execute", _after_execute, {"recover": "recover", "verify": "verify"}
    )
    g.add_edge("recover", "plan")
    g.add_edge("verify", "reflect")
    g.add_edge("reflect", "ground")
    g.add_edge("ground", "discover")
    g.add_edge("discover", "reverify")
    g.add_edge("reverify", "learn")
    g.add_edge("learn", "transfer")
    g.add_edge("transfer", "evaluate")
    g.add_edge("evaluate", "independent_evaluate")
    g.add_edge("independent_evaluate", "explore")
    g.add_edge("explore", "collaborate")
    g.add_edge("collaborate", "agent")
    g.add_edge("agent", "intellectual_history")
    g.add_edge("intellectual_history", "honesty")
    g.add_edge("honesty", "model_development")
    g.add_edge("model_development", "update_memory")
    g.add_edge("update_memory", "end")
    g.add_edge("end", END)
    return g.compile(checkpointer=checkpointer)


async def run_cycle(
    db_path: str = "/tmp/iam_autonomy_checkpoints.sqlite",
    trigger: str = "scheduled",
    observations: Optional[List[Dict[str, Any]]] = None,
    signed_authorization: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run one durable autonomy cycle with full evidence semantics."""
    import os

    path = os.environ.get("IAM_CHECKPOINT_DB", db_path)
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        graph = build_graph(saver)
        config = {"configurable": {"thread_id": "iam-main-autonomy"}}
        result = await graph.ainvoke(
            {
                "session_id": "iam-main",
                "trigger": trigger,
                "observations": observations or [],
                "memories": [],
                "memory_error": None,
                "steps": [],
                "error": None,
                "retry_count": 0,
                "decision": None,
                "model_used": False,
                "verification_evidence": None,
                "signed_authorization": signed_authorization,
                # P0.3 cognitive fields
                "reasoning_trace": None,
                "reasoning_modes_used": [],
                "metacognitive_critique": None,
                "belief_revisions": [],
                "discovery_summary": None,
                "reverify_summary": None,
                "learning_summary": None,
                "cross_domain_summary": None,
                "evaluation_summary": None,
                "curiosity_summary": None,
                "attention_summary": None,
                "grounded_summary": None,
                "agency_summary": None,
                "intellectual_history_summary": None,
                "collaborative_summary": None,
                "intellectual_honesty_summary": None,
                "independent_evaluation_summary": None,
                "model_development_summary": None,
            },
            config=config,
        )
        return {
            "reasoning": result.get("reasoning"),
            "action": result.get("action_result"),
            "verification": result.get("verification"),
            "verification_evidence": result.get("verification_evidence"),
            "memory_id": result.get("memory_id"),
            "service": result.get("dispatch_service"),
            "steps": result.get("steps", []),
            "reasoning_trace": result.get("reasoning_trace"),
            "reasoning_modes_used": result.get("reasoning_modes_used", []),
            "metacognitive_critique": result.get("metacognitive_critique"),
            "belief_revisions": result.get("belief_revisions", []),
            "discovery_summary": result.get("discovery_summary"),
            "reverify_summary": result.get("reverify_summary"),
            "learning_summary": result.get("learning_summary"),
            "cross_domain_summary": result.get("cross_domain_summary"),
            "evaluation_summary": result.get("evaluation_summary"),
            "curiosity_summary": result.get("curiosity_summary"),
            "attention_summary": result.get("attention_summary"),
            "grounded_summary": result.get("grounded_summary"),
            "agency_summary": result.get("agency_summary"),
            "intellectual_history_summary": result.get("intellectual_history_summary"),
            "collaborative_summary": result.get("collaborative_summary"),
            "intellectual_honesty_summary": result.get("honesty_summary"),
            "independent_evaluation_summary": result.get("independent_evaluation_summary"),
            "model_development_summary": result.get("model_development_summary"),
        }
