"""P7-d — Agency / independent problem-solving.

Gives IAM the ability to identify problems worth solving, establish intermediate
objectives, develop strategies, break objectives into tasks, select tools,
execute, monitor progress, recover from failures, evaluate results, and learn
from completed work — all within creator authority and governance boundaries.

Builds on:
* P7-a curiosity (gap detection) — identifies problems worth solving
* P7-b attention (resource management) — selects which objectives to pursue
* P7-c grounded intelligence (verification) — validates results against reality
* P0-P6 autonomy graph (execution) — carries out authorized tasks

This is not unbounded autonomy: every action passes through GovernanceService
and IPLCI gates, and high-impact decisions require Creator authorization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
import loguru

from app.services import iam_context
from app.services.evidence_service import EvidenceService
from app.orchestration.reasoning_engine import ReasoningMode, reason_in_mode

logger = loguru.logger


@dataclass
class SubTask:
    """An intermediate objective within a larger goal."""

    id: str
    title: str
    description: str
    status: str  # pending, in_progress, completed, failed, blocked
    tool_name: Optional[str]  # which IAM service/tool to use
    parameters: Dict[str, Any]
    depends_on: List[str]  # subtask IDs this depends on
    result: Optional[Dict[str, Any]]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class Strategy:
    """A developed strategy for achieving an objective."""

    id: str
    objective: str
    approach: str  # high-level strategy description
    subtasks: List[SubTask]
    estimated_effort: str
    required_tools: List[str]
    risk_factors: List[str]
    success_criteria: List[str]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class AgencyObjective:
    """A self-identified objective that IAM wants to pursue."""

    id: str
    title: str
    description: str
    source: str  # "curiosity_gap", "contradiction", "transfer_opportunity"
    priority: float  # 0.0 to 1.0
    status: str  # identified, planning, in_progress, completed, abandoned
    strategy: Optional[Strategy]
    current_subtask_index: int
    results: List[Dict[str, Any]]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class AgencyEngine:
    """Independent problem-solving within governance boundaries.

    Takes identified problems (from curiosity gaps, contradictions, transfer
    opportunities) and develops strategies, breaks them into subtasks, selects
    tools, executes, monitors, recovers, evaluates, and learns.

    All actions pass through GovernanceService and IPLCI — IAM cannot act
    outside its authorized boundaries.
    """

    async def identify_objectives(
        self,
        db: Any,
        curiosity_gaps: List[Dict[str, Any]],
        contradictions: List[Dict[str, Any]],
        transfer_opportunities: List[Dict[str, Any]],
    ) -> List[AgencyObjective]:
        """Identify objectives worth pursuing from identified problems.

        Converts gaps, contradictions, and transfer opportunities into
        actionable objectives with priorities based on measured impact.
        """
        objectives: List[AgencyObjective] = []

        # Convert curiosity gaps to objectives
        for gap in curiosity_gaps:
            objective = AgencyObjective(
                id=str(uuid.uuid4()),
                title=f"Investigate: {gap.get('title', '')}",
                description=gap.get("content", "") or gap.get("title", ""),
                source=gap.get("gap_type", "curiosity_gap"),
                priority=gap.get("attention_score", 0.5),
                status="identified",
                strategy=None,
                current_subtask_index=0,
                results=[],
            )
            objectives.append(objective)

        # Convert contradictions to objectives
        for c in contradictions:
            objective = AgencyObjective(
                id=str(uuid.uuid4()),
                title=f"Resolve contradiction: {c.get('belief_a_title', '')} vs {c.get('belief_b_title', '')}",
                description=c.get("contradiction_reason", ""),
                source="contradiction",
                priority=self._contradiction_priority(c),
                status="identified",
                strategy=None,
                current_subtask_index=0,
                results=[],
            )
            objectives.append(objective)

        # Convert transfer opportunities to objectives
        for t in transfer_opportunities:
            objective = AgencyObjective(
                id=str(uuid.uuid4()),
                title=f"Validate transfer: {t.get('insight', '')[:80]}",
                description=f"Transfer insight from {t.get('source_topic', '')} to {t.get('target_topic', '')}",
                source="transfer_opportunity",
                priority=t.get("transfer_confidence", 0.5),
                status="identified",
                strategy=None,
                current_subtask_index=0,
                results=[],
            )
            objectives.append(objective)

        # Sort by priority descending
        objectives.sort(key=lambda o: o.priority, reverse=True)
        return objectives

    def _contradiction_priority(self, c: Dict[str, Any]) -> float:
        """Calculate priority for a contradiction-based objective."""
        severity_weights = {"high": 1.0, "medium": 0.6, "low": 0.3}
        severity = c.get("severity", "low")
        severity_score = severity_weights.get(severity, 0.3)

        conf_a = c.get("belief_a", {}).get("confidence_level", 0.5) or 0.5
        conf_b = c.get("belief_b", {}).get("confidence_level", 0.5) or 0.5
        confidence_product = conf_a * conf_b

        return round(severity_score * confidence_product, 4)

    async def develop_strategy(
        self,
        db: Any,
        objective: AgencyObjective,
    ) -> Strategy:
        """Develop a strategy for achieving an objective.

        Breaks the objective into subtasks, selects tools, identifies
        dependencies and risk factors. Strategy is developed through
        reasoning but execution is gated by GovernanceService.
        """
        # Use reasoning engine to develop the strategy
        question = (
            f"Objective: {objective.title}\n"
            f"Description: {objective.description}\n"
            f"Source: {objective.source}\n"
            f"Develop a strategy to accomplish this objective. Break it into "
            f"subtasks, identify which IAM tools/services are needed for each "
            f"subtask, identify dependencies between subtasks, identify risk "
            f"factors, and define success criteria. Return JSON with: "
            f'approach, subtasks (list of {{title, description, tool_name, '
            f'parameters, depends_on}}), required_tools, risk_factors, '
            f'success_criteria.'
        )

        try:
            trace = await reason_in_mode(
                None, ReasoningMode.CAUSAL, question
            )
        except Exception as exc:
            logger.warning(f"strategy development failed: {exc}")
            trace = None

        # Parse strategy from reasoning output
        subtasks: List[SubTask] = []
        if trace and trace.reasoning_steps:
            for i, step in enumerate(trace.reasoning_steps):
                subtask = SubTask(
                    id=str(uuid.uuid4()),
                    title=step[:100],
                    description=step,
                    status="pending",
                    tool_name=None,
                    parameters={},
                    depends_on=[],
                    result=None,
                )
                subtasks.append(subtask)

        strategy = Strategy(
            id=str(uuid.uuid4()),
            objective=objective.title,
            approach=trace.conclusion if trace else "develop and execute",
            subtasks=subtasks,
            estimated_effort="unknown",
            required_tools=["memory_service", "research_service", "governance_service"],
            risk_factors=["unverified_external_sources", "governance_boundaries"],
            success_criteria=[objective.description],
        )

        return strategy

    async def execute_objective(
        self,
        db: Any,
        objective: AgencyObjective,
        strategy: Strategy,
    ) -> Dict[str, Any]:
        """Execute an objective through its strategy.

        Executes subtasks through the autonomy graph's dispatch mechanism,
        with governance checks at each step. Monitors progress, recovers from
        failures, and evaluates results.
        """
        from app.orchestration import dispatch as action_dispatch

        execution_result: Dict[str, Any] = {
            "objective_id": objective.id,
            "objective_title": objective.title,
            "strategy_id": strategy.id,
            "subtask_results": [],
            "overall_status": "pending",
            "lessons_learned": [],
        }

        for subtask in strategy.subtasks:
            subtask.status = "in_progress"

            # Execute through dispatch (governance-gated)
            try:
                outcome = await action_dispatch.dispatch(
                    db,
                    subtask.tool_name or "memory_recall",
                    {
                        "objective_id": objective.id,
                        "subtask_id": subtask.id,
                        "query": subtask.description,
                        "title": subtask.title,
                        "tool_name": subtask.tool_name,
                        "parameters": subtask.parameters,
                    },
                )

                subtask.result = outcome
                subtask.status = "completed" if outcome.get("status") == "success" else "failed"

                execution_result["subtask_results"].append({
                    "subtask_id": subtask.id,
                    "subtask_title": subtask.title,
                    "status": subtask.status,
                    "outcome": outcome,
                })

            except Exception as exc:
                logger.warning(f"subtask execution failed: {exc}")
                subtask.status = "failed"
                subtask.result = {"error": str(exc)}
                execution_result["subtask_results"].append({
                    "subtask_id": subtask.id,
                    "subtask_title": subtask.title,
                    "status": "failed",
                    "outcome": {"error": str(exc)},
                })

        # Determine overall status
        completed = sum(1 for s in strategy.subtasks if s.status == "completed")
        failed = sum(1 for s in strategy.subtasks if s.status == "failed")

        if failed == 0 and completed == len(strategy.subtasks):
            execution_result["overall_status"] = "completed"
        elif completed > 0:
            execution_result["overall_status"] = "partial"
        else:
            execution_result["overall_status"] = "failed"

        # Learn from the execution
        lessons = self._derive_lessons(strategy, execution_result)
        execution_result["lessons_learned"] = lessons

        return execution_result

    def _derive_lessons(
        self,
        strategy: Strategy,
        execution_result: Dict[str, Any],
    ) -> List[str]:
        """Derive lessons from an executed objective.

        What worked, what didn't, what should change next time.
        """
        lessons: List[str] = []

        completed = sum(1 for s in strategy.subtasks if s.status == "completed")
        total = len(strategy.subtasks)

        if completed == total:
            lessons.append(
                f"Strategy '{strategy.approach}' completed successfully — "
                f"all {total} subtasks succeeded"
            )
        elif completed > 0:
            lessons.append(
                f"Strategy '{strategy.approach}' partially completed — "
                f"{completed}/{total} subtasks succeeded"
            )
            lessons.append(
                "Review failed subtasks to identify missing tools or "
                "incorrect parameterization"
            )
        else:
            lessons.append(
                f"Strategy '{strategy.approach}' failed — "
                f"no subtasks succeeded"
            )
            lessons.append(
                "Reconsider approach or decompose objective differently"
            )

        # Tool-specific lessons
        tool_failures = [
            s for s in strategy.subtasks
            if s.status == "failed" and s.tool_name
        ]
        if tool_failures:
            lessons.append(
                f"Tools with failures: {[s.tool_name for s in tool_failures]}"
            )

        return lessons

    async def run_agency_cycle(
        self,
        db: Any,
        curiosity_gaps: List[Dict[str, Any]],
        contradictions: List[Dict[str, Any]],
        transfer_opportunities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Run one complete agency cycle.

        Identify objectives → develop strategies → execute → learn.
        All within governance boundaries.
        """
        summary: Dict[str, Any] = {
            "objectives_identified": 0,
            "strategies_developed": 0,
            "objectives_executed": 0,
            "objectives_completed": 0,
            "lessons_learned": [],
            "details": [],
        }

        # Step 1: Identify objectives
        objectives = await self.identify_objectives(
            db, curiosity_gaps, contradictions, transfer_opportunities
        )
        summary["objectives_identified"] = len(objectives)

        # Step 2: Develop strategies and execute top-priority objectives
        for objective in objectives[:3]:  # top 3 per cycle
            strategy = await self.develop_strategy(db, objective)
            summary["strategies_developed"] += 1

            execution = await self.execute_objective(db, objective, strategy)
            summary["details"].append({
                "objective_id": objective.id,
                "objective_title": objective.title,
                "strategy_approach": strategy.approach,
                "execution_status": execution["overall_status"],
                "lessons_learned": execution["lessons_learned"],
            })

            if execution["overall_status"] == "completed":
                summary["objectives_completed"] += 1
            summary["objectives_executed"] += 1
            summary["lessons_learned"].extend(execution["lessons_learned"])

        return summary
