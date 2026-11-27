"""LangGraph durable autonomy workflow.

Stateful, checkpointed operational loop replacing the simple sleep loop.
States: observe → retrieve → reason → identify → plan → authority → execute →
verify → reflect → memory → (continue | recover | rest).

Every cognitive stage performs real work: memory retrieval calls MemoryService,
reasoning calls the shared model resolver with an explicit offline fallback,
planning selects an allowlisted subsystem action, execution calls that service
and persists an evidence record, verification re-reads the persisted evidence,
and consolidation stores only verified outcomes as experience memory.

The orchestrator itself is provider-independent. A missing model never produces
fabricated reasoning, and an unverified action is never marked complete.
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

logger = loguru.logger

MAX_RETRIES = 1

ALLOWED_MODEL_ACTIONS = set(action_dispatch.AVAILABLE) | {
    "observe",
    "ask_authorization",
}


class AutonomyState(TypedDict):
    """State carried through the autonomy workflow."""

    session_id: str
    trigger: str
    observations: List[dict]
    memories: List[dict]
    memory_error: Optional[str]
    reasoning: Optional[str]
    decision: Optional[dict]
    model_used: bool
    inference_mode: Optional[str]
    objectives: List[dict]
    plan: Optional[dict]
    authority_check: Optional[dict]
    governance_context: Optional[Dict[str, Any]]
    action_result: Optional[dict]
    verification: Optional[str]
    verification_evidence: Optional[dict]
    reflection: Optional[str]
    decision_id: Optional[str]
    memory_id: Optional[str]
    retry_count: int
    error: Optional[str]
    steps: Annotated[List[str], operator.add]


def _session():
    """Return a fresh database session context without importing at module load."""
    from app.core.database import get_session_factory

    return get_session_factory()()


def _query_from(observations: List[dict], limit: int = 3) -> str:
    return " ".join(
        str(item.get("title") or item.get("content") or "")
        for item in (observations or [])[:limit]
    ).strip()


async def observe(state: AutonomyState) -> dict:
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


async def retrieve_memory(state: AutonomyState) -> dict:
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


async def reason(state: AutonomyState) -> dict:
    """Reason via the shared model resolver, with an honest offline fallback."""
    obs = state.get("observations", [])
    if not obs:
        return {
            "reasoning": "No active work; conserve resources.",
            "decision": {"action": "observe", "confidence": 0.0},
            "model_used": False,
            "inference_mode": "offline",
            "steps": ["reason:idle"],
        }

    from app.services.model_inference import InferenceUnavailable, inference_service

    system_prompt = (
        "You are IAM's autonomy orchestrator. Choose one safe next action from: "
        + ", ".join(sorted(ALLOWED_MODEL_ACTIONS))
        + ". Never grant yourself permissions, spend funds or change protected "
        "configuration. Return JSON only: "
        '{"action": str, "reasoning": str, "confidence": number 0-1}.'
    )
    memory_lines = "\n".join(
        f"- {item.get('content', '')[:160]}" for item in state.get("memories", [])[:3]
    ) or "No relevant memories."
    user_prompt = (
        f"Active work: {_query_from(obs, 5)[:500]}\n"
        f"Relevant memories: {memory_lines[:500]}\n"
        f"Retry count: {state.get('retry_count', 0)}"
    )

    try:
        status = await inference_service.resolve()
        if not status.available:
            raise InferenceUnavailable(status.reason)
        result = await inference_service.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=256,
            timeout=60.0,
        )
        content = str(result["choices"][0]["message"]["content"]).strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start < 0 or end <= start:
                raise
            parsed = json.loads(content[start : end + 1])
        action = str(parsed.get("action", "observe"))
        if action not in ALLOWED_MODEL_ACTIONS:
            action = "observe"
        confidence = max(0.0, min(1.0, float(parsed.get("confidence", 0.5))))
        return {
            "reasoning": str(parsed.get("reasoning", ""))[:1000],
            "decision": {"action": action, "confidence": confidence},
            "model_used": True,
            "inference_mode": status.mode,
            "steps": ["reason:model"],
        }
    except Exception as exc:
        # No fabricated reasoning and no autonomous action without a model.
        return {
            "reasoning": (
                f"model unavailable; no autonomous action inferred: "
                f"{type(exc).__name__}: {exc}"
            )[:1000],
            "decision": {"action": "observe", "confidence": 0.0},
            "model_used": False,
            "inference_mode": "offline",
            "steps": ["reason:offline"],
        }


async def identify_objectives(state: AutonomyState) -> dict:
    """Select objectives — pending tasks first, then goals."""
    tasks = [o for o in state.get("observations", []) if o.get("type") == "task"]
    objectives = tasks[:3] or state.get("observations", [])[:3]
    return {"objectives": objectives, "steps": ["identify_objectives"]}


def _infer_action(objective: dict, decision: Optional[dict]) -> str:
    preferred = (decision or {}).get("action")
    if preferred in action_dispatch.AVAILABLE:
        return str(preferred)
    tool_name = str(objective.get("tool_name") or "")
    if tool_name in action_dispatch.AVAILABLE:
        return tool_name
    title = str(objective.get("title") or "").lower()
    if "research" in title:
        return "research"
    if "memory" in title:
        return "memory_recall"
    if "capab" in title:
        return "capability_inspect"
    if "permission" in title or "authority" in title:
        return "governance_check"
    return "model_probe"


async def plan(state: AutonomyState) -> dict:
    """Convert the selected objective into an actionable, allowlisted plan."""
    obj = (state.get("objectives") or [None])[0]
    if not obj:
        return {"plan": None, "steps": ["plan:skip"]}
    action = _infer_action(obj, state.get("decision"))
    return {
        "plan": {
            "objective": obj,
            "action": action,
            "steps": ["authorize", f"dispatch:{action}", "verify", "consolidate"],
            "expected_evidence": f"decision_outcome:{obj.get('id')}",
        },
        "steps": ["plan"],
    }


async def check_authority(state: AutonomyState) -> dict:
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


async def execute(state: AutonomyState) -> dict:
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

        governance_context = state.get("governance_context") or {}
        governance_step = "iplci:no_context"
        if governance_context.get("source_id"):
            from app.services.iplci.gateway import GovernanceRefusal
            from app.services.iplci.integration import enforce_agent_request

            try:
                await enforce_agent_request(
                    db,
                    action=action,
                    source_id=governance_context["source_id"],
                    agent_id=str(governance_context.get("agent_id") or "main"),
                    jurisdiction=governance_context.get("jurisdiction"),
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


async def recover(state: AutonomyState) -> dict:
    """Bounded recovery: record the failure and allow one retry."""
    return {
        "retry_count": int(state.get("retry_count", 0)) + 1,
        "steps": ["recover"],
    }


async def verify(state: AutonomyState) -> dict:
    """Verify the outcome by re-reading the persisted execution evidence."""
    from app.models.autonomy import DecisionRecord

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
            if payload.get("status") == "success" and payload.get("evidence"):
                return {
                    "verification": "verified_by_execution_evidence",
                    "verification_evidence": {
                        "decision_id": decision_id,
                        "service": result.get("service"),
                        "evidence": payload["evidence"],
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


async def reflect(state: AutonomyState) -> dict:
    """Reflect on the verified outcome and record a real reflection entry."""
    from app.models.reflection import ReflectionEntry

    async with _session() as db:
        db.add(
            ReflectionEntry(
                reflection_type="experience",
                title="Autonomy cycle",
                content=json.dumps(
                    {
                        "verification": state.get("verification"),
                        "evidence": state.get("verification_evidence"),
                        "memory_error": state.get("memory_error"),
                    },
                    ensure_ascii=False,
                )[:2000],
                lesson_learned=state.get("reasoning"),
                confidence=float((state.get("decision") or {}).get("confidence", 0.5)),
            )
        )
        await db.commit()
    return {"reflection": "recorded", "steps": ["reflect"]}


async def update_memory(state: AutonomyState) -> dict:
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


async def end_cycle(state: AutonomyState) -> dict:
    return {"steps": ["end"]}


def _after_execute(state: AutonomyState) -> str:
    result = state.get("action_result") or {}
    if result.get("status") in ("failed", "blocked") and int(state.get("retry_count", 0)) < MAX_RETRIES:
        return "recover"
    return "verify"


def build_graph(checkpointer: AsyncSqliteSaver):
    """Compile the durable autonomy graph."""
    g = StateGraph(AutonomyState)
    for name, node in (
        ("observe", observe),
        ("retrieve_memory", retrieve_memory),
        ("reason", reason),
        ("identify_objectives", identify_objectives),
        ("plan", plan),
        ("check_authority", check_authority),
        ("execute", execute),
        ("recover", recover),
        ("verify", verify),
        ("reflect", reflect),
        ("update_memory", update_memory),
        ("end", end_cycle),
    ):
        g.add_node(name, node)

    g.add_edge(START, "observe")
    g.add_edge("observe", "retrieve_memory")
    g.add_edge("retrieve_memory", "reason")
    g.add_edge("reason", "identify_objectives")
    g.add_edge("identify_objectives", "plan")
    g.add_edge("plan", "check_authority")
    g.add_edge("check_authority", "execute")
    g.add_conditional_edges(
        "execute", _after_execute, {"recover": "recover", "verify": "verify"}
    )
    g.add_edge("recover", "plan")
    g.add_edge("verify", "reflect")
    g.add_edge("reflect", "update_memory")
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
        }
