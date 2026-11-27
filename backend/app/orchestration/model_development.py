"""P7-h — Foundation Model Development and Self-Improvement.

IAM's cognitive layer for developing its own primary foundation model
(Qwen2.5-3B). This module deliberately contains **no second training
pipeline**: it delegates to the existing ``app.services.ai_research`` stack —
dataset building, SFT/QLoRA training, reproducible benchmarks and the signed
release gate — and adds only the cognitive loop (assess → identify gaps →
prepare candidates → record evidence).

Invariants:

* Candidate preparation is autonomous; production promotion is not. Promotion
  goes through ``ModelReleaseService.promote``, which requires an active signed
  Creator authorization covering the exact ``model@version``.
* Absence of measurement is not evidence of a capability gap. Only assessed
  domains with real held-out evidence can motivate weight changes.
* Missing training inputs produce an explicit ``blocked`` result, never a
  fabricated job record or a silent no-op.
* Identity, memory, beliefs, knowledge and goals are independent of the model
  version and survive every replacement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import json
import uuid

import loguru

from app.core.config import settings
from app.services import iam_context
from app.services import serving_model
from app.services.ai_research import self_improvement
from app.services.ai_research.release_gate import (
    ModelReleaseService,
    default_release_store,
)
from sqlalchemy.ext.asyncio import AsyncSession

logger = loguru.logger

DEFAULT_BASE_MODEL = "qwen2.5:3b"
WEAKNESS_THRESHOLD = 0.7
MAX_CANDIDATES_PER_CYCLE = 3
DEFAULT_DOMAINS = [
    "reasoning",
    "mathematics",
    "coding",
    "scientific_knowledge",
    "instruction_following",
    "tool_use",
    "knowledge_retention",
    "creative_writing",
    "self_evaluation",
    "cross_lingual",
]


@dataclass
class CapabilityAssessment:
    """A measured capability of IAM's current foundation model."""

    model_id: str
    capability: str
    score: float
    confidence: float
    evidence: str
    dataset: str
    assessed_at: str


class FoundationModelDeveloper:
    """Orchestrates foundation-model development through the existing stack.

    Training adapters, a trusted evaluator, a served candidate alias, a
    checkpoint reference and a licence must be supplied by the operator (or a
    higher-level governed workflow); without them the developer reports what is
    missing instead of pretending work happened.
    """

    def __init__(
        self,
        db: AsyncSession,
        *,
        adapters: Optional[List[Any]] = None,
        evaluate: Optional[Any] = None,
        store: Optional[Any] = None,
        checkpoint_ref: str = "",
        candidate_model: str = "",
        licence: str = "",
        governance_context: Optional[Dict[str, Any]] = None,
        evaluator_provenance: Optional[Dict[str, Any]] = None,
        actor: str = "iam",
    ):
        self.db = db
        self.base_model = (
            getattr(settings, "iam_primary_local_tag", None) or DEFAULT_BASE_MODEL
        )
        self.adapters = list(adapters or [])
        self.evaluate = evaluate
        self.store = store or default_release_store()
        self.checkpoint_ref = checkpoint_ref
        self.candidate_model = candidate_model
        self.licence = licence
        self.governance_context = governance_context
        # Identity/checksum of the trusted evaluator, recorded in benchmark
        # evidence so a score cannot be attributed to an unknown judge.
        self.evaluator_provenance = dict(evaluator_provenance or {})
        self.actor = actor
        # One release service per developer: the registry keeps in-memory
        # active-version state that must survive across promote/rollback calls.
        self._release = ModelReleaseService(self.db, self.store)

    # ------------------------------------------------------------------
    # Capability assessment
    # ------------------------------------------------------------------

    async def assess_capabilities(
        self,
        model_id: str,
        domains: Optional[List[str]] = None,
    ) -> List[CapabilityAssessment]:
        """Assess all requested domains from one held-out evaluation run.

        Running the full suite once per domain would repeat the same expensive
        evaluation ten times and discard nine results each time.
        """
        from app.orchestration.evaluation_suite import EvaluationSuite

        domains = list(domains or DEFAULT_DOMAINS)
        report = await EvaluationSuite(self.db).run_evaluation()
        by_domain = {item.domain: item for item in report.domains}

        assessments: List[CapabilityAssessment] = []
        for domain in domains:
            result = by_domain.get(domain)
            if result is None:
                assessment = CapabilityAssessment(
                    model_id=model_id,
                    capability=domain,
                    score=0.0,
                    confidence=0.0,
                    evidence=f"No held-out evaluation data for domain {domain}",
                    dataset="held_out_eval",
                    assessed_at=datetime.now(timezone.utc).isoformat(),
                )
            else:
                assessment = CapabilityAssessment(
                    model_id=model_id,
                    capability=domain,
                    score=float(result.score),
                    confidence=float(result.score),
                    evidence=(
                        f"Independent held-out evaluation: {result.score} score "
                        f"({result.correct}/{result.total} correct)"
                    ),
                    dataset="held_out_eval",
                    assessed_at=datetime.now(timezone.utc).isoformat(),
                )
            assessments.append(assessment)

            await iam_context.record_belief(
                self.db,
                title=f"Capability assessment: {assessment.capability}",
                content=json.dumps(assessment.__dict__, indent=2, default=str),
                source="foundation_model_development",
                confidence_level=assessment.confidence,
                topic="model_capability_assessment",
                belief_type="measurement",
                provenance="foundation_model_development",
                evidence=[{
                    "type": "capability_assessment",
                    "capability": assessment.capability,
                    "score": assessment.score,
                    "confidence": assessment.confidence,
                    "evidence": assessment.evidence,
                    "dataset": assessment.dataset,
                    "model": model_id,
                }],
            )

        return assessments

    # ------------------------------------------------------------------
    # Candidate preparation (delegated to the real research pipeline)
    # ------------------------------------------------------------------

    def _missing_inputs(self) -> List[str]:
        reasons: List[str] = []
        if not self.adapters:
            reasons.append("no eligible training adapter with a driver is configured")
        elif not any(
            bool(getattr(adapter, "credentials_available", lambda: False)())
            for adapter in self.adapters
        ):
            # default_adapters() returns platform adapters, but only those with
            # a configured driver can actually provision a training job.
            reasons.append("no research platform adapter has a configured driver")
        if self.evaluate is None:
            reasons.append("no trusted evaluator is configured")
        if not self.checkpoint_ref.strip():
            reasons.append("no checkpoint reference for a served candidate")
        if not self.candidate_model.strip():
            reasons.append("no served alias for the candidate checkpoint")
        if not self.licence.strip():
            reasons.append("no licence for the training dataset")
        return reasons

    async def prepare_candidate(
        self,
        weakness: CapabilityAssessment,
        *,
        baseline_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Prepare one benchmarked candidate. Never promotes it.

        Delegates dataset building, training, benchmarking and registration to
        ``self_improvement.prepare_candidate``. Missing inputs fail closed with
        an explicit reason.
        """
        missing = self._missing_inputs()
        baseline = weakness.score if baseline_score is None else baseline_score
        if baseline <= 0:
            missing.append("no measured positive baseline score")
        if missing:
            return {
                "status": "blocked",
                "capability": weakness.capability,
                "reasons": missing,
            }

        from app.services.ai_research.benchmarks import BenchmarkSpec

        benchmark_spec = BenchmarkSpec(
            name=f"{weakness.capability}-regression",
            task_type=weakness.capability,
            repetitions=2,
            # A supplied callable is a "custom" evaluator to BenchmarkRunner.
            # The trusted evaluator's identity/checksum still travels in the
            # config so the resulting evidence records who produced the score.
            evaluator="custom",
            config=dict(self.evaluator_provenance),
        )
        request = self_improvement.CandidateRequest(
            experiment_id=f"dev_{uuid.uuid4().hex}",
            licence=self.licence,
            base_model=self.base_model,
            candidate_model=self.candidate_model,
            checkpoint_ref=self.checkpoint_ref,
            baseline_score=float(baseline),
            task_type=weakness.capability,
            benchmark_spec=benchmark_spec,
            diagnosis=(
                f"held-out weakness: {weakness.capability} scored {weakness.score}"
            ),
        )
        try:
            return await self_improvement.prepare_candidate(
                self.db,
                request,
                store=self.store,
                adapters=self.adapters,
                evaluate=self.evaluate,
                actor=self.actor,
                governance_context=self.governance_context,
            )
        except Exception as exc:  # research errors must not abort the cycle
            logger.warning(f"candidate preparation failed: {exc}")
            return {
                "status": "failed",
                "capability": weakness.capability,
                "error": f"{type(exc).__name__}: {exc}",
            }

    # ------------------------------------------------------------------
    # Governed release operations (delegated to the signed release gate)
    # ------------------------------------------------------------------

    async def promote(
        self,
        model: str,
        version: str,
        benchmark_refs: List[str],
    ) -> Dict[str, Any]:
        """Promote through the signed Creator authorization gate.

        There is deliberately no ``creator_approved`` boolean here: authority
        is checked by ``ModelReleaseService`` against an active signed
        authorization for this exact ``model@version``.
        """
        return await self._release.promote(
            model, version, benchmark_refs, self.actor
        )

    async def rollback(
        self,
        model: str,
        version: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Roll back through the same signed authorization gate."""
        # Recover active state from durable artifacts (e.g. after a restart)
        # rather than relying only on this process's in-memory registry.
        self._release.registry.hydrate()
        return await self._release.rollback(
            model, version, reason, self.actor
        )

    async def active_model(self) -> Dict[str, Any]:
        """Return the actually served model, not a hard-coded claim."""
        current = serving_model.current().as_dict()
        return {**current, "deployment_status": "production"}

    # ------------------------------------------------------------------
    # Development cycle
    # ------------------------------------------------------------------

    async def run_development_cycle(
        self,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Assess → identify measured gaps → prepare candidates. Never promotes."""
        session = db or self.db
        summary: Dict[str, Any] = {
            "assessments": [],
            "candidates_prepared": 0,
            "candidates": [],
            "blocked": [],
            "details": [],
            "promoted": False,
        }

        assessments = await self.assess_capabilities(self.base_model)
        summary["assessments"] = [
            {
                "capability": a.capability,
                "score": a.score,
                "confidence": a.confidence,
            }
            for a in assessments
        ]

        # No measurement is not evidence of a gap: confidence 0 must never
        # trigger a weight change.
        weaknesses = [
            a for a in assessments
            if a.confidence > 0 and a.score < WEAKNESS_THRESHOLD
        ][:MAX_CANDIDATES_PER_CYCLE]

        for weakness in weaknesses:
            result = await self.prepare_candidate(weakness)
            if result.get("status") == "candidate":
                summary["candidates_prepared"] += 1
                summary["candidates"].append({
                    "capability": weakness.capability,
                    "model": result.get("model"),
                    "version": result.get("version"),
                    "post_score": result.get("post_score"),
                })
            else:
                summary["blocked"].append({
                    "capability": weakness.capability,
                    "status": result.get("status"),
                    "reasons": result.get("reasons") or [result.get("error", "")],
                })
            summary["details"].append({
                "capability": weakness.capability,
                "score": weakness.score,
                "status": result.get("status"),
            })

        return summary
