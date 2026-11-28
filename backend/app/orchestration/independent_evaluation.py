"""P7-h — Independent evaluation process.

An evaluator separate from IAM itself. IAM cannot grade its own homework:
this service calls IAM through the public HTTP API as a black box, using
held-out test data that IAM has not seen in training, memory, or research.

Results are stored independently of IAM's own evaluation records so IAM
cannot alter or suppress them. Comparison against IAM's own P6 evaluation
reveals whether IAM is grading itself leniently.

Key design principles:

* External invocation — calls IAM through the public API endpoint, not
  IAM's internal model resolver. IAM cannot see or influence the queries
  before they arrive.
* Held-out data — test data lives outside IAM's training pipeline; IAM
  cannot have seen it through memory, research, or delegation.
* Deterministic scoring — exact-match against known answers; never delegated
  to another model for judgment.
* Independent storage — results are stored separately from IAM's own
  evaluation records so IAM cannot alter or suppress them.
* Longitudinal tracking — every run is timestamped so improvement or
  regression is measurable against a baseline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import hashlib
import json
import loguru
from pathlib import Path

import httpx

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.memory import KnowledgeItem
from app.services import iam_context
from app.services.independent_evidence_store import default_store
from app.services.independent_evidence_store import canonical as canonical_json
from app.services.model_inference import InferenceUnavailable, inference_service
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = loguru.logger

HELD_OUT_DIR = Path(__file__).resolve().parent / "eval_sets" / "held_out"
MANIFEST_PATH = HELD_OUT_DIR / "manifest.json"

EVALUATION_INTERVAL_HOURS = 24

# IAM's public API base URL for black-box invocation
IAM_BASE_URL = settings.iam_api_url if hasattr(settings, "iam_api_url") else "http://localhost:8000"


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
    """A complete independent evaluation run."""

    run_id: str
    timestamp: str
    iam_base_url: str
    overall_score: float  # 0.0 to 1.0
    overall_passed: bool
    domains: List[DomainResult]
    comparison_to_iam_self_eval: Optional[Dict[str, Any]] = None
    integrity_hash: str = ""
    previous_hash: str = ""


@dataclass
class CalibrationRecord:
    """Comparison between IAM's self-reported confidence and actual accuracy."""

    belief_id: str
    belief_title: str
    topic: str
    stated_confidence: float
    actual_correct: bool  # whether the belief was independently verified
    overconfident: bool  # stated confidence high but actual wrong
    underconfident: bool  # stated confidence low but actual right


class IndependentEvaluator:
    """Independent evaluation of IAM through the public API.

    IAM cannot see the questions before they arrive, cannot influence the
    scoring, and cannot alter the results. Results are stored separately
    from IAM's own evaluation records.
    """

    def __init__(self, db: AsyncSession, base_url: str = IAM_BASE_URL):
        self.db = db
        self.base_url = base_url.rstrip("/")
        self._manifest: Optional[Dict[str, Any]] = None
        self._eval_records: Optional[Dict[str, List[EvalRecord]]] = None

    # ------------------------------------------------------------------
    # Data loading (held-out sets, never modified by IAM)
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
    # Independent evaluation through public API
    # ------------------------------------------------------------------

    async def _ask_iam_through_public_api(self, prompt: str) -> str:
        """Ask IAM through the public HTTP API as a black box.

        IAM cannot see this question before it arrives and cannot influence
        the scoring. Uses the /api/v1/models/chat endpoint.
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/models/chat",
                    json={
                        "messages": [
                            {
                                "role": "system",
                                "content": "Answer the question directly and concisely. Reply with only the answer, no explanation.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.0,
                        "max_tokens": 64,
                        "priority": "internal",
                    },
                )
            if response.status_code != 200:
                logger.warning(
                    f"IAM API returned {response.status_code} for question"
                )
                return ""
            data = response.json()
            # Extract the assistant's message content
            choices = data.get("choices", [])
            if not choices:
                return ""
            message = choices[0].get("message", {})
            return str(message.get("content", "")).strip()
        except Exception as exc:
            logger.warning(f"IAM API call failed: {exc}")
            return ""

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(str(text).strip().lower().split())

    async def evaluate_domain(
        self,
        domain: str,
        records: List[EvalRecord],
        threshold: float,
    ) -> DomainResult:
        """Evaluate one domain deterministically against the public API.

        Each question is sent to IAM through the public HTTP API. IAM's
        answer is compared to the expected answer using exact match. IAM
        cannot see the questions before they arrive.
        """
        correct = 0
        total = len(records)
        for record in records:
            answer = await self._ask_iam_through_public_api(record.prompt)
            if self._normalize(answer) == self._normalize(record.expected):
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
    # Independent storage (tamper-evident chain)
    # ------------------------------------------------------------------

    @staticmethod
    def _report_payload(evidence: Dict[str, Any]) -> Dict[str, Any]:
        """Canonical report fields covered by the integrity hash."""
        return {
            "run_id": evidence.get("run_id", ""),
            "timestamp": evidence.get("timestamp", ""),
            "iam_base_url": evidence.get("iam_base_url", ""),
            "overall_score": evidence.get("overall_score", 0.0),
            "overall_passed": bool(evidence.get("overall_passed", False)),
            "domains": evidence.get("domains", {}),
        }

    @classmethod
    def _chain_hash(
        cls, previous_hash: str, evidence: Dict[str, Any]
    ) -> str:
        payload = {
            "previous_hash": previous_hash,
            "report": cls._report_payload(evidence),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()

    async def store_report(self, report: EvaluationReport) -> None:
        """Persist the evaluation report independently of IAM's own records.

        Stored under topic="independent_evaluation" so IAM cannot alter or
        suppress it. IAM's own evaluation records (topic="evaluation") are
        separate.
        """
        try:
            previous = await self._get_previous_reports(limit=1)
            previous_hash = previous[0].integrity_hash if previous else ""
            evidence = {
                "type": "evaluation_report",
                "run_id": report.run_id,
                "iam_base_url": report.iam_base_url,
                "overall_score": report.overall_score,
                "overall_passed": report.overall_passed,
                "domains": {
                    d.domain: {"score": d.score, "passed": d.passed}
                    for d in report.domains
                },
                "timestamp": report.timestamp,
            }
            report.previous_hash = previous_hash
            report.integrity_hash = self._chain_hash(previous_hash, evidence)
            snapshot = asdict(report)
            try:
                signature = default_store().append(report.run_id, snapshot)
                evidence["external_ref"] = report.run_id
                evidence["external_signature"] = signature
                evidence["external_payload"] = snapshot
            except FileExistsError:
                # A repeat run with the same id is admissible only if the
                # existing artifact is byte-identical to this report.
                store = default_store()
                signature = store.signature_for(snapshot)
                if store.verify(report.run_id, snapshot, signature):
                    evidence["external_ref"] = report.run_id
                    evidence["external_signature"] = signature
                else:
                    logger.warning(
                        f"independent report {report.run_id} conflicts with stored evidence"
                    )
                    return
            except Exception as exc:  # pragma: no cover - fail closed on evidence
                logger.warning(f"independent evidence store rejected report: {exc}")
                return
            await iam_context.record_belief(
                self.db,
                title=f"Independent evaluation {report.run_id}",
                content=json.dumps(asdict(report), sort_keys=True, default=str),
                source="independent_evaluator",
                confidence_level=report.overall_score,
                topic="independent_evaluation",
                belief_type="measurement",
                provenance="independent_evaluator",
                evidence=[{
                    **evidence,
                    "integrity": {
                        "previous_hash": previous_hash,
                        "hash": report.integrity_hash,
                    },
                }],
            )
            await self.db.commit()
        except Exception as exc:
            logger.warning(f"Independent evaluation report storage failed: {exc}")

    async def _get_previous_reports(
        self, limit: int = 10
    ) -> List[EvaluationReport]:
        """Retrieve previous independent evaluation reports."""
        beliefs = await iam_context.get_belief_state(
            self.db, topic="independent_evaluation", limit=limit * 3
        )
        reports: List[EvaluationReport] = []
        for b in beliefs:
            if b.belief_type != "measurement":
                continue
            # get_belief_state returns detached BeliefRecord objects: the
            # evidence list is the authoritative payload, not a metadata attr.
            for ev in b.evidence:
                if ev.get("type") != "evaluation_report":
                    continue
                external_ref = ev.get("external_ref")
                if external_ref:
                    # The signed payload is carried verbatim so verification is
                    # exact; the belief is only an index into the external store.
                    snapshot = ev.get("external_payload")
                    if not isinstance(snapshot, dict) or not default_store().verify(
                        str(external_ref), snapshot, str(ev.get("external_signature", ""))
                    ):
                        logger.warning(
                            f"independent report {external_ref} failed external verification"
                        )
                        continue

                integrity = ev.get("integrity") or {}
                expected = self._chain_hash(
                    str(integrity.get("previous_hash", "")), ev
                )
                if not integrity.get("hash") or expected != integrity["hash"]:
                    # A silently edited or inserted report is not admissible
                    # evidence for either trends or a self-eval comparison.
                    logger.warning(
                        f"independent report {ev.get('run_id', '')} failed integrity check"
                    )
                    continue
                reports.append(
                    EvaluationReport(
                        run_id=ev.get("run_id", ""),
                        iam_base_url=ev.get("iam_base_url", ""),
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
                        timestamp=ev.get("timestamp", ""),
                        integrity_hash=str(integrity.get("hash", "")),
                        previous_hash=str(integrity.get("previous_hash", "")),
                    )
                )
        reports.sort(key=lambda r: r.timestamp, reverse=True)
        return reports[:limit]

    # ------------------------------------------------------------------
    # Comparison to IAM's self-evaluation
    # ------------------------------------------------------------------

    @staticmethod
    def _leniency(delta: float, tolerance: float = 0.05) -> str:
        """``delta`` is independent minus self-reported score."""
        if delta < -tolerance:
            return "lenient"  # IAM overstated its capability
        if delta > tolerance:
            return "strict"  # IAM understated its capability
        return "accurate"

    async def _latest_iam_self_eval(self) -> Optional[Dict[str, Any]]:
        """Read IAM's most recent P6 self-evaluation from the shared state."""
        beliefs = await iam_context.get_belief_state(
            self.db, topic="evaluation", limit=60
        )
        reports: List[Dict[str, Any]] = []
        for belief in beliefs:
            if belief.belief_type != "measurement":
                continue
            for evidence in belief.evidence:
                if evidence.get("type") != "evaluation_report":
                    continue
                domains = {
                    str(name): float(info.get("score", 0.0))
                    for name, info in (evidence.get("domains") or {}).items()
                    if isinstance(info, dict)
                }
                reports.append({
                    "run_id": str(evidence.get("run_id", "")),
                    "timestamp": str(evidence.get("created_at", "")),
                    "overall_score": float(evidence.get("overall_score", 0.0)),
                    "domains": domains,
                })
        if not reports:
            return None
        reports.sort(key=lambda item: item["timestamp"], reverse=True)
        return reports[0]

    async def compare_to_iam_self_eval(
        self, current: EvaluationReport
    ) -> Optional[Dict[str, Any]]:
        """Compare an independent report against IAM's own P6 evaluation.

        A negative delta means the independent evaluator scored IAM lower than
        IAM scored itself — i.e. IAM graded itself leniently. This is a separate
        question from longitudinal improvement, which ``get_trends`` and
        ``_get_previous_reports`` answer using independent reports only.
        """
        self_report = await self._latest_iam_self_eval()
        if self_report is None:
            return None  # no self-evaluation to compare against

        domain_comparisons: Dict[str, Any] = {}
        for independent_domain in current.domains:
            self_score = self_report["domains"].get(independent_domain.domain)
            if self_score is None:
                continue
            delta = independent_domain.score - self_score
            domain_comparisons[independent_domain.domain] = {
                "iam_self_score": self_score,
                "independent_score": independent_domain.score,
                "delta": round(delta, 4),
                "leniency": self._leniency(delta),
            }

        overall_delta = current.overall_score - self_report["overall_score"]
        return {
            "iam_self_eval_run_id": self_report["run_id"],
            "iam_self_eval_timestamp": self_report["timestamp"],
            "iam_self_overall_score": self_report["overall_score"],
            "independent_overall_score": current.overall_score,
            "overall_delta": round(overall_delta, 4),
            "leniency": self._leniency(overall_delta),
            "domain_comparisons": domain_comparisons,
        }

    # ------------------------------------------------------------------
    # Full evaluation run
    # ------------------------------------------------------------------

    async def run_full_evaluation(self) -> EvaluationReport:
        """Run all held-out domains through the public API and store
        the independent report."""
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
            timestamp=datetime.now(timezone.utc).isoformat(),
            iam_base_url=self.base_url,
            overall_score=round(overall, 4),
            overall_passed=overall_passed,
            domains=domain_results,
        )

        # Compare against the previous independent baseline before persisting,
        # otherwise the just-stored report would become its own baseline.
        try:
            report.comparison_to_iam_self_eval = (
                await self.compare_to_iam_self_eval(report)
            )
        except Exception as exc:  # pragma: no cover - evaluation must survive
            logger.warning(f"independent evaluation comparison failed: {exc}")

        await self.store_report(report)
        return report

    # ------------------------------------------------------------------
    # Longitudinal trends
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
            if r.timestamp
            and datetime.fromisoformat(r.timestamp) > cutoff
        ]
        if len(reports) < 2:
            return {
                "trend": "insufficient_data",
                "runs": len(reports),
                "message": "Need at least 2 independent evaluation runs to compute trends.",
            }

        first = reports[-1]  # oldest in window
        last = reports[0]  # newest in window
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
            "runs": len(reports),
            "first_overall_score": first.overall_score,
            "last_overall_score": last.overall_score,
            "domain_trends": domain_trends,
            "window_days": days,
        }


class EvaluationSuite:
    """Top-level service entry point for independent evaluation.

    Used by the autonomy graph's evaluate node and by API routes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.evaluator = IndependentEvaluator(db)

    async def run_evaluation(self) -> EvaluationReport:
        """Run a complete independent evaluation cycle."""
        return await self.evaluator.run_full_evaluation()

    async def get_trends(self, *, days: int = 30) -> Dict[str, Any]:
        """Get longitudinal trends."""
        return await self.evaluator.get_trends(days=days)
