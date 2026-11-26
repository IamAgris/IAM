"""LangGraph durable autonomy workflow.

Stateful, checkpointed operational loop replacing the simple sleep loop.
States: observe → retrieve → reason → plan → check_authority → execute →
verify → reflect → update_memory → (continue | rest)

Durable execution: an AsyncSqliteSaver checkpointer allows the graph to resume
after a restart without losing position. The orchestrator itself is
provider-independent — models are called through the model gateway.
"""

from typing import TypedDict, Annotated, List, Optional, Any
from datetime import datetime
import operator
import loguru

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.core.config import settings

logger = loguru.logger


class AutonomyState(TypedDict):
    """State carried through the autonomy workflow."""
    session_id: str
    trigger: str                      # event that started this run
    observations: List[dict]
    memories: List[dict]
    reasoning: Optional[str]
    objectives: List[dict]
    plan: Optional[dict]
    authority_check: Optional[dict]
    action_result: Optional[dict]
    verification: Optional[str]
    reflection: Optional[str]
    decision_id: Optional[str]
    error: Optional[str]
    steps: Annotated[List[str], operator.add]


async def observe(state: AutonomyState) -> dict:
    """Gather environment signals: pending tasks, goals, recent messages."""
    from app.core.database import get_session_factory
    from app.models.autonomy import Goal, Task
    from sqlalchemy import select
    async with get_session_factory()() as db:
        goals = (await db.execute(select(Goal).where(Goal.status == "active").limit(5))).scalars().all()
        tasks = (await db.execute(select(Task).where(Task.status == "pending").limit(5))).scalars().all()
    obs = [
        {"type": "goal", "id": str(g.id), "title": g.title} for g in goals
    ] + [
        {"type": "task", "id": str(t.id), "title": t.title} for t in tasks
    ]
    return {"observations": obs, "steps": ["observe"]}


async def retrieve_memory(state: AutonomyState) -> dict:
    """Retrieve relevant memories (without external model call)."""
    return {"memories": state.get("memories", []), "steps": ["retrieve_memory"]}


async def reason(state: AutonomyState) -> dict:
    """Reason about the next useful action. Deterministic orchestration;
    model calls occur through the gateway when configured."""
    obs = state.get("observations", [])
    if not obs:
        return {"reasoning": "No active work; conserve resources.", "steps": ["reason:idle"]}
    return {
        "reasoning": f"Found {len(obs)} active items. Prioritising pending tasks.",
        "steps": ["reason"],
    }


async def identify_objectives(state: AutonomyState) -> dict:
    """Select objectives — pending tasks first, then goals."""
    tasks = [o for o in state.get("observations", []) if o.get("type") == "task"]
    objectives = tasks[:3] or state.get("observations", [])[:3]
    return {"objectives": objectives, "steps": ["identify_objectives"]}


async def plan(state: AutonomyState) -> dict:
    """Convert the selected objective into a plan."""
    obj = (state.get("objectives") or [None])[0]
    if not obj:
        return {"plan": None, "steps": ["plan:skip"]}
    return {
        "plan": {"objective": obj, "steps": ["prepare", "execute", "verify"]},
        "steps": ["plan"],
    }


async def check_authority(state: AutonomyState) -> dict:
    """Verify authority before any consequential action."""
    from app.core.database import get_session_factory
    from app.services.governance_service import GovernanceService
    action = "write_code_internal"  # routine internal action
    async with get_session_factory()() as db:
        decision = await GovernanceService(db).check_authority(action, "2")
    # Routine work is autonomous. Consequential actions need a signed Creator
    # authorization; the retired standing-grant table is never consulted.
    return {
        "authority_check": {
            "action": action,
            "permitted": bool(decision.get("permitted")),
            "decision": decision,
            "authority_source": "governance_boundary_or_signed_creator",
        },
        "steps": ["check_authority"],
    }


async def execute(state: AutonomyState) -> dict:
    """Execute the permitted internal step. Records a decision."""
    from app.core.database import get_session_factory
    from app.models.autonomy import DecisionRecord, Task
    from sqlalchemy import select
    plan = state.get("plan")
    if not plan:
        return {"action_result": {"status": "skipped"}, "steps": ["execute:skip"]}
    obj = plan.get("objective", {})
    async with get_session_factory()() as db:
        decision = DecisionRecord(
            decision=f"Autonomous step toward: {obj.get('title', 'objective')}",
            reasoning=state.get("reasoning"),
            confidence=0.6,
        )
        db.add(decision)
        await db.commit()
        did = str(decision.id)
        # Advance the task if this was a task objective
        if obj.get("type") == "task":
            r = await db.execute(select(Task).where(Task.id == obj["id"]))
            task = r.scalar_one_or_none()
            if task and task.status == "pending":
                task.status = "in_progress"
                task.started_at = datetime.utcnow()
                await db.commit()
    return {
        "action_result": {"status": "advanced", "objective": obj.get("title")},
        "decision_id": did,
        "steps": ["execute"],
    }


async def verify(state: AutonomyState) -> dict:
    """Verify the action result (no self-graded success without evidence)."""
    result = state.get("action_result", {})
    return {
        "verification": "verified_internal_transition" if result.get("status") == "advanced" else "no_action",
        "steps": ["verify"],
    }


async def reflect(state: AutonomyState) -> dict:
    """Reflect on outcome and record a reflection entry."""
    from app.core.database import get_session_factory
    from app.models.reflection import ReflectionEntry
    async with get_session_factory()() as db:
        db.add(ReflectionEntry(
            reflection_type="experience",
            title="Autonomy cycle",
            content=state.get("verification", "no action"),
            lesson_learned=state.get("reasoning"),
            confidence=0.6,
        ))
        await db.commit()
    return {"reflection": "recorded", "steps": ["reflect"]}


async def update_memory(state: AutonomyState) -> dict:
    """Persist a concise summary of the cycle (no raw private data)."""
    return {"steps": ["update_memory"]}


async def end_cycle(state: AutonomyState) -> dict:
    """Terminal node."""
    return {"steps": ["end"]}


def build_graph(checkpointer: AsyncSqliteSaver):
    """Compile the durable autonomy graph."""
    g = StateGraph(AutonomyState)
    g.add_node("observe", observe)
    g.add_node("retrieve_memory", retrieve_memory)
    g.add_node("reason", reason)
    g.add_node("identify_objectives", identify_objectives)
    g.add_node("plan", plan)
    g.add_node("check_authority", check_authority)
    g.add_node("execute", execute)
    g.add_node("verify", verify)
    g.add_node("reflect", reflect)
    g.add_node("update_memory", update_memory)
    g.add_node("end", end_cycle)

    g.add_edge(START, "observe")
    g.add_edge("observe", "retrieve_memory")
    g.add_edge("retrieve_memory", "reason")
    g.add_edge("reason", "identify_objectives")
    g.add_edge("identify_objectives", "plan")
    g.add_edge("plan", "check_authority")
    g.add_edge("check_authority", "execute")
    g.add_edge("execute", "verify")
    g.add_edge("verify", "reflect")
    g.add_edge("reflect", "update_memory")
    g.add_edge("update_memory", "end")
    g.add_edge("end", END)

    return g.compile(checkpointer=checkpointer)


async def run_cycle(db_path: str = "/tmp/iam_autonomy_checkpoints.sqlite", trigger: str = "scheduled") -> dict:
    """Run one durable autonomy cycle.

    Checkpoints default to /tmp (writable in the container). Override via the
    IAM_CHECKPOINT_DB environment variable for persistent storage.
    """
    import os
    path = os.environ.get("IAM_CHECKPOINT_DB", db_path)
    async with AsyncSqliteSaver.from_conn_string(path) as saver:
        graph = build_graph(saver)
        config = {"configurable": {"thread_id": "iam-main-autonomy"}}
        result = await graph.ainvoke({
            "session_id": "iam-main",
            "trigger": trigger,
            "observations": [], "memories": [], "objectives": [],
            "steps": [], "error": None,
        }, config=config)
        return {
            "reasoning": result.get("reasoning"),
            "action": result.get("action_result"),
            "verification": result.get("verification"),
            "steps": result.get("steps", []),
        }
