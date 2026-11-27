"""P6 — Longitudinal evaluation service.

Independent evaluation of IAM's capability improvement over time, using
held-out test data that IAM has not seen in training or memory. Results
are stored in the shared epistemic state (topic="evaluation") so
longitudinal trends are measurable and auditable.

Key design principles:

* Held-out data: eval sets live outside IAM's training pipeline; the model
  cannot have seen them through memory, research, or delegation.
* Deterministic scoring: exact-match against known answers; never delegated
  to another model for judgment.
* Independent verification: scores are numeric facts, not self-reported
  capability claims.
* Longitudinal tracking: every run is timestamped and stored so improvement
  (or regression) is measurable against a baseline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import hashlib
import json
import loguru
from pathlib import Path

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.memory import KnowledgeItem
from app.services import iam_context
from app.services.model_inference import InferenceUnavailable, inference_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = loguru.logger

HELD_OUT_DIR = Path(__file__).resolve().parent / "eval_sets" / "held_out"
MANIFEST_PATH = HELD_OUT_DIR / "manifest.json"

EVALUATION_INTERVAL_HOURS = 24


@dataclass
class EvalRecord:
    """A single evaluation question and expected answer."""

    prompt: str
    expected: str
    domain: str
    task_type: str
    difficulty: str


@dataclass
class DomainResult:
    """Evaluation result for one domain."""

    domain: str
    score: float  # 0.0 to 1.0
    total: int
    correct: int
    threshold: float
    passed: bool
    dataset_sha256: str


@dataclass
class EvaluationReport:
    """A complete longitudinal evaluation run."""

    run_id: str
    model: str
    overall_score: float
    overall_passed: bool
    domains: List[DomainResult]
    created_at: str
    compared_to_baseline: Optional[Dict[str, Any]] = None


class LongitudinalEvaluator:
    """Runs held-out evaluations and tracks capability over time."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._manifest: Optional[Dict[str, Any]] = None
        self._eval_records: Optional[Dict[str, List[EvalRecord]]] = None

    # ------------------------------------------------------------------
    # Data loading (held-out sets, never modified by IAM's training)
    # ------------------------------------------------------------------

    async def _load_manifest(self) -> Dict[str, Any]:
        if self._manifest is None:
            raw = MANIFEST_PATH.read_bytes()
            self._manifest = json.loads(raw.decode("utf-8"))
        return self._manifest

    async def _load_records(self) -> Dict[str, List[EvalRecord]]:
        if self._eval_records is not None:
            return self._eval_records
        manifest = await self._load_manifest()
        records: Dict[str, List[EvalRecord]] = {}
        for suite in manifest["suites"]:
            dataset_path = HELD_OUT_DIR / suite["dataset"]
            raw = dataset_path.read_bytes()
            sha256 = hashlib.sha256(raw).hexdigest()
            suite_records: List[EvalRecord] = []
            for line in raw.decode("utf-8").splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                suite_records.append(
                    EvalRecord(
                        prompt=str(item["prompt"]),
                        expected=str(item["expected"]),
                        domain=str(item.get("domain", suite["name"])),
                        task_type=str(item.get("task_type", "unknown")),
                        difficulty=str(item.get("difficulty", "unknown")),
                    )
                )
            records[suite["name"]] = suite_records
            records[suite["name"]][0].__dict__["_sha256"] = sha256  # type: ignore[attr-defined]
        self._eval_records = records
        return records

    async def _dataset_sha256(self, domain: str) -> str:
        manifest = await self._load_manifest()
        for suite in manifest["suites"]:
            if suite["name"] == domain:
                dataset_path = HELD_OUT_DIR / suite["dataset"]
                return hashlib.sha256(dataset_path.read_bytes()).hexdigest()
        raise ValueError(f"unknown domain: {domain}")

    # ------------------------------------------------------------------
    # Deterministic scoring against the local model
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(text: str) -> str:
        return " ".join(str(text).strip().lower().split())

    async def _ask_model(self, prompt: str) -> str:
        """Ask the local model directly — no delegation, no other model judges."""
        try:
            status = await inference_service.resolve()
            if not status.available:
                raise InferenceUnavailable(status.reason)
            result = await inference_service.chat(
                [
                    {
                        "role": "system",
                        "content": "Answer the question directly and concisely. Reply with only the answer, no explanation.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=64,
                timeout=30.0,
                db=self.db,
            )
            return str(result["choices"][0]["message"]["content"]).strip()
        except Exception as exc:
            logger.warning(f"model query failed: {exc}")
            return ""

    async def evaluate_domain(
        self,
        domain: str,
        records: List[EvalRecord],
        threshold: float,
    ) -> DomainResult:
        """Evaluate one domain deterministically against the local model."""
        correct = 0
        total = len(records)
        for record in records:
            answer = await self._ask_model(record.prompt)
            if self._normalise(answer) == self._normalise(record.expected):
                correct += 1
        score = correct / total if total > 0 else 0.0
        sha256 = await self._dataset_sha256(domain)
        return DomainResult(
            domain=domain,
            score=round(score, 4),
            total=total,
            correct=correct,
            threshold=threshold,
            passed=score >= threshold,
            dataset_sha256=sha256,
        )

    # ------------------------------------------------------------------
    # Longitudinal storage and comparison
    # ------------------------------------------------------------------

    async def store_report(self, report: EvaluationReport) -> None:
        """Persist the evaluation report to the shared epistemic state."""
        await iam_context.record_belief(
            self.db,
            title=f"Evaluation run {report.run_id}",
            content=json.dumps(asdict(report), sort_keys=True, default=str),
            source="evaluation_suite",
            confidence_level=report.overall_score,
            topic="evaluation",
            belief_type="measurement",
            provenance="longitudinal_evaluator",
            evidence=[
                {
                    "type": "evaluation_report",
                    "run_id": report.run_id,
                    "model": report.model,
                    "overall_score": report.overall_score,
                    "overall_passed": report.overall_passed,
                    "domains": {
                        d.domain: {"score": d.score, "passed": d.passed}
                        for d in report.domains
                    },
                    "created_at": report.created_at,
                }
            ],
        )
        await self.db.commit()

    async def _get_previous_reports(
        self, limit: int = 10
    ) -> List[EvaluationReport]:
        """Retrieve previous evaluation reports from the shared epistemic state."""
        beliefs = await iam_context.get_belief_state(
            self.db, topic="evaluation", limit=limit * 3
        )
        reports: List[EvaluationReport] = []
        for b in beliefs:
            if b.belief_type != "measurement":
                continue
            # get_belief_state returns detached BeliefRecord objects.
            for ev in b.evidence:
                if ev.get("type") == "evaluation_report":
                    reports.append(
                        EvaluationReport(
                            run_id=ev.get("run_id", ""),
                            model=ev.get("model", ""),
                            overall_score=float(ev.get("overall_score", 0.0)),
                            overall_passed=bool(ev.get("overall_passed", False)),
                            domains=[
                                DomainResult(
                                    domain=d,
                                    score=float(s.get("score", 0.0)),
                                    total=0,
                                    correct=0,
                                    threshold=0.0,
                                    passed=bool(s.get("passed", False)),
                                    dataset_sha256="",
                                )
                                for d, s in ev.get("domains", {}).items()
                            ],
                            created_at=ev.get("created_at", ""),
                        )
                    )
        reports.sort(key=lambda r: r.created_at, reverse=True)
        return reports[:limit]

    async def compare_to_baseline(
        self, current: EvaluationReport
    ) -> Optional[Dict[str, Any]]:
        """Compare current results to the most recent previous run.

        Returns improvement/decline per domain and overall.
        """
        previous = await self._get_previous_reports(limit=2)
        if len(previous) < 2:
            return None  # no baseline yet
        prev = previous[1]  # most recent before current
        domain_comparisons: Dict[str, Any] = {}
        for cur_domain in current.domains:
            prev_domain = next(
                (d for d in prev.domains if d.domain == cur_domain.domain), None
            )
            if prev_domain is None:
                continue
            delta = cur_domain.score - prev_domain.score
            domain_comparisons[cur_domain.domain] = {
                "previous_score": prev_domain.score,
                "current_score": cur_domain.score,
                "delta": round(delta, 4),
                "improved": delta > 0,
                "regressed": delta < -0.05,
            }
        overall_delta = current.overall_score - prev.overall_score
        return {
            "baseline_run_id": prev.run_id,
            "baseline_created_at": prev.created_at,
            "overall_delta": round(overall_delta, 4),
            "overall_improved": overall_delta > 0,
            "overall_regressed": overall_delta < -0.05,
            "domain_comparisons": domain_comparisons,
        }

    # ------------------------------------------------------------------
    # Full evaluation run
    # ------------------------------------------------------------------

    async def run_full_evaluation(self) -> EvaluationReport:
        """Run all held-out domains and store the longitudinal report."""
        manifest = await self._load_manifest()
        records = await self._load_records()

        domain_results: List[DomainResult] = []
        for suite in manifest["suites"]:
            domain = suite["name"]
            domain_records = records.get(domain, [])
            threshold = float(suite.get("threshold", 0.0))
            result = await self.evaluate_domain(
                domain, domain_records, threshold
            )
            domain_results.append(result)

        overall = (
            sum(d.score for d in domain_results) / len(domain_results)
            if domain_results
            else 0.0
        )
        overall_passed = all(d.passed for d in domain_results)

        run_id = hashlib.sha256(
            f"{datetime.now(timezone.utc).isoformat()}{overall}".encode()
        ).hexdigest()[:16]

        report = EvaluationReport(
            run_id=run_id,
            model="local-qwen-3b",
            overall_score=round(overall, 4),
            overall_passed=overall_passed,
            domains=domain_results,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Compare to baseline
        report.compared_to_baseline = await self.compare_to_baseline(report)

        # Store in shared epistemic state
        await self.store_report(report)

        return report

    # ------------------------------------------------------------------
    # Trend analysis
    # ------------------------------------------------------------------

    async def get_trends(
        self, *, days: int = 30
    ) -> Dict[str, Any]:
        """Return longitudinal trends over the given number of days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        reports = await self._get_previous_reports(limit=50)
        recent = [
            r
            for r in reports
            if r.created_at
            and datetime.fromisoformat(r.created_at) > cutoff
        ]
        if len(recent) < 2:
            return {
                "trend": "insufficient_data",
                "runs": len(recent),
                "message": "Need at least 2 evaluation runs to compute trends.",
            }

        first = recent[-1]  # oldest in window
        last = recent[0]  # newest in window
        overall_delta = last.overall_score - first.overall_score

        domain_trends: Dict[str, Any] = {}
        for d in last.domains:
            first_d = next(
                (x for x in first.domains if x.domain == d.domain), None
            )
            if first_d is None:
                continue
            domain_trends[d.domain] = {
                "first_score": first_d.score,
                "last_score": d.score,
                "delta": round(d.score - first_d.score, 4),
                "improved": d.score > first_d.score,
            }

        return {
            "trend": (
                "improving"
                if overall_delta > 0.02
                else "declining"
                if overall_delta < -0.02
                else "stable"
            ),
            "overall_delta": round(overall_delta, 4),
            "runs": len(recent),
            "first_overall_score": first.overall_score,
            "last_overall_score": last.overall_score,
            "domain_trends": domain_trends,
            "window_days": days,
        }


class EvaluationSuite:
    """Top-level service entry point for longitudinal evaluation.

    Used by the autonomy graph's evaluate node and by API routes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.evaluator = LongitudinalEvaluator(db)

    async def run_evaluation(self) -> EvaluationReport:
        """Run a complete longitudinal evaluation cycle."""
        return await self.evaluator.run_full_evaluation()

    async def get_trends(self, *, days: int = 30) -> Dict[str, Any]:
        """Get longitudinal trends."""
        return await self.evaluator.get_trends(days=days)
