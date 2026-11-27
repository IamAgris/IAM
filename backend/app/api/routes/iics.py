"""IICS foundation API — pending proposal overlay inside existing systems."""

import base64
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.iics import (
    ActionLedger,
    AdvisoryIngestor,
    BenchmarkCase,
    BenchmarkSuite,
    BudgetLimit,
    ConfidenceCalibrator,
    CreatorEmailBridge,
    DLPEngine,
    EgressGateway,
    MediaDocumentService,
    MediaError,
    PermissionGate,
    PrivacyLifecycle,
    ScheduledResearchError,
    ScheduledResearchService,
    SitePolicyStore,
    SourceRegistry,
    StrategySelector,
    label_for_confidence,
)
from app.models.iics import IICSBenchmarkResult

router = APIRouter(prefix="/api/v1/iics", tags=["iics-foundation"])


class EgressRequest(BaseModel):
    url: str


class AuthorizeRequest(BaseModel):
    action_type: str
    url: Optional[str] = None
    purpose: str = "public research"
    jurisdiction: Optional[str] = None


class ActionRequest(BaseModel):
    actor: str
    tool: str
    target: str
    idempotency_key: str
    scope: str = "public"
    permission_source: str = "legal_gateway"
    approval_ref: Optional[str] = None
    bytes_transferred: int = 0
    cost_units: int = 0


class SourceRequest(BaseModel):
    url: str
    source_type: str = "public_web"
    licence: Optional[str] = None
    rights: Dict[str, bool] = {}
    territory: Optional[str] = None
    freshness_class: str = "documentation"
    reliability_score: float = 0.0
    conditions: List[str] = []
    legal_audit_event_id: Optional[str] = None


class ClaimRequest(BaseModel):
    claim: str
    confidence: float
    locator: Optional[str] = None
    publication_date: Optional[str] = None
    label: Optional[str] = None


@router.post("/egress/check")
async def check_egress(payload: EgressRequest) -> Dict[str, Any]:
    """Deterministically assess a URL without performing a request."""
    return EgressGateway().assess(payload.url).as_dict()


@router.post("/authorize")
async def authorize(payload: AuthorizeRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """Combine internet permission with the mandatory legal gateway."""
    return await PermissionGate(db).authorize(
        payload.action_type,
        payload.url,
        purpose=payload.purpose,
        jurisdiction=payload.jurisdiction,
    )


@router.post("/actions")
async def record_action(payload: ActionRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    if payload.scope != "public" and not payload.approval_ref:
        raise HTTPException(status_code=403, detail="approval_ref required for non-public scope")
    return await ActionLedger(db).record(**payload.model_dump())


@router.get("/actions")
async def list_actions(db: AsyncSession = Depends(get_db_session)) -> List[Dict[str, Any]]:
    return await ActionLedger(db).list()


@router.get("/actions/budget")
async def action_budget(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    ledger = ActionLedger(db)
    usage = await ledger.usage()
    allowed, reason = await ledger.check_budget(BudgetLimit())
    return {"usage": usage, "allowed": allowed, "reason": reason}


@router.post("/sources")
async def register_source(payload: SourceRequest, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    return await SourceRegistry(db).register(**payload.model_dump())


@router.get("/sources")
async def list_sources(active_only: bool = False, db: AsyncSession = Depends(get_db_session)) -> List[Dict[str, Any]]:
    return await SourceRegistry(db).list(active_only=active_only)


@router.get("/sources/{source_id}")
async def get_source(source_id: str, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    source = await SourceRegistry(db).get(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="source_not_found")
    return source


@router.post("/sources/{source_id}/refresh")
async def refresh_source(source_id: str, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    if not await SourceRegistry(db).touch(source_id):
        raise HTTPException(status_code=404, detail="source_not_found")
    return {"status": "refreshed"}


@router.post("/sources/{source_id}/revoke")
async def revoke_source(source_id: str, db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    try:
        return await SourceRegistry(db).revoke(source_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sources/{source_id}/claims")
async def add_claim(
    source_id: str, payload: ClaimRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    try:
        return await SourceRegistry(db).add_claim(source_id, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/sources/{source_id}/claims")
async def list_claims(source_id: str, db: AsyncSession = Depends(get_db_session)) -> List[Dict[str, Any]]:
    return await SourceRegistry(db).claims(source_id)


class StrategyRequest(BaseModel):
    question: str
    known_domains: List[str] = []
    prior_confidence: Optional[float] = None
    prefer_depth: bool = False


class ConfidenceRequest(BaseModel):
    sources: List[Dict[str, Any]]


class ScheduledTaskRequest(BaseModel):
    goal: str
    query: str
    cadence_minutes: int = 1440
    freshness_class: str = "documentation"
    task_id: Optional[str] = None


class TaskStatusRequest(BaseModel):
    status: str


@router.post("/research/strategy")
async def select_strategy(payload: StrategyRequest) -> Dict[str, Any]:
    return StrategySelector().select(
        payload.question,
        known_domains=payload.known_domains,
        prior_confidence=payload.prior_confidence,
        prefer_depth=payload.prefer_depth,
    ).as_dict()


@router.post("/research/confidence")
async def calibrate_confidence(payload: ConfidenceRequest) -> Dict[str, Any]:
    score = ConfidenceCalibrator.score(payload.sources)
    return {
        "score": score,
        "label": ConfidenceCalibrator.label(score),
        "sufficient_for_commit": ConfidenceCalibrator.sufficient_for_commit(score),
    }


@router.post("/scheduled")
async def create_scheduled_task(
    payload: ScheduledTaskRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    try:
        return await ScheduledResearchService(db).create(
            payload.goal,
            payload.query,
            cadence_minutes=payload.cadence_minutes,
            freshness_class=payload.freshness_class,
            task_id=payload.task_id,
        )
    except ScheduledResearchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/scheduled")
async def list_scheduled_tasks(db: AsyncSession = Depends(get_db_session)) -> List[Dict[str, Any]]:
    return await ScheduledResearchService(db).list()


@router.get("/scheduled/due")
async def due_scheduled_tasks(db: AsyncSession = Depends(get_db_session)) -> List[Dict[str, Any]]:
    return await ScheduledResearchService(db).due()


@router.post("/scheduled/{task_id}/status")
async def set_scheduled_status(
    task_id: str,
    payload: TaskStatusRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        changed = await ScheduledResearchService(db).set_status(task_id, payload.status)
    except ScheduledResearchError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not changed:
        raise HTTPException(status_code=404, detail="task_not_found")
    return {"task_id": task_id, "status": payload.status}


class MediaExtractRequest(BaseModel):
    content_b64: str
    content_type: str = ""
    filename: str = ""
    allow_ocr: bool = False


class AdvisoryIngestRequest(BaseModel):
    payload: Dict[str, Any]
    source: str = "osv"


class DLPCheckRequest(BaseModel):
    text: str
    channel: str = "api"


class SitePolicyRequest(BaseModel):
    domain: str
    robots_text: str = ""
    terms_text: str = ""
    ttl_hours: int = 720
    source_url: Optional[str] = None
    notes: Optional[str] = None


class PrivacyRecordRequest(BaseModel):
    kind: str
    subject_ref: str
    jurisdiction: Optional[str] = None
    details: Dict[str, Any] = {}


class PrivacyResolveRequest(BaseModel):
    evidence: Dict[str, Any]
    status: str = "resolved"


@router.post("/media/extract")
async def extract_media(payload: MediaExtractRequest) -> Dict[str, Any]:
    """Extract text/metadata locally. Content remains untrusted data."""
    try:
        raw = base64.b64decode(payload.content_b64, validate=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_base64") from exc
    try:
        return MediaDocumentService().prepare(
            raw,
            content_type=payload.content_type,
            filename=payload.filename,
            allow_ocr=payload.allow_ocr,
        )
    except MediaError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/security/advisories/ingest")
async def ingest_advisories(
    payload: AdvisoryIngestRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    return await AdvisoryIngestor(db).ingest(payload.payload, payload.source)


@router.get("/security/advisories")
async def list_advisories(db: AsyncSession = Depends(get_db_session)) -> List[Dict[str, Any]]:
    return await AdvisoryIngestor(db).list()


@router.post("/security/dlp/check")
async def check_dlp(
    payload: DLPCheckRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    outcome = DLPEngine.check(payload.text, payload.channel)
    await DLPEngine.record(db, outcome, {"path": "/security/dlp/check"})
    return outcome


@router.post("/site-policies")
async def record_site_policy(
    payload: SitePolicyRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    try:
        return await SitePolicyStore(db).record(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/site-policies/stale")
async def stale_site_policies(db: AsyncSession = Depends(get_db_session)) -> List[Dict[str, Any]]:
    return await SitePolicyStore(db).list_stale()


@router.get("/site-policies/{domain}")
async def get_site_policy(
    domain: str, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    policy = await SitePolicyStore(db).get(domain)
    if not policy:
        raise HTTPException(status_code=404, detail="policy_not_found")
    return policy


@router.post("/privacy/records")
async def open_privacy_record(
    payload: PrivacyRecordRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    try:
        return await PrivacyLifecycle(db).open(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/privacy/records/{record_id}/resolve")
async def resolve_privacy_record(
    record_id: str,
    payload: PrivacyResolveRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        changed = await PrivacyLifecycle(db).resolve(
            record_id, payload.evidence, status=payload.status
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not changed:
        raise HTTPException(status_code=404, detail="record_not_found")
    return {"record_id": record_id, "status": payload.status}


@router.get("/privacy/transfer-permitted")
async def transfer_permitted(
    subject_ref: str,
    jurisdiction: str,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    allowed = await PrivacyLifecycle(db).transfer_permitted(subject_ref, jurisdiction)
    return {"permitted": allowed, "subject_ref": subject_ref, "jurisdiction": jurisdiction}


class CreatorNotifyRequest(BaseModel):
    update: str
    context: Optional[str] = None


class QAAlertRequest(BaseModel):
    regressions: List[str]
    results: List[Dict[str, Any]] = []


class MonitoringDigestRequest(BaseModel):
    items: List[Dict[str, Any]]


class CreatorApprovalRequest(BaseModel):
    action_type: str
    summary: str
    target_ref: Optional[str] = None
    consequences: List[str] = []
    risk_level: str = "3"
    reason: Optional[str] = None


@router.post("/creator/notify")
async def notify_creator(
    payload: CreatorNotifyRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Send an informational Creator email. It grants no authority."""
    return await CreatorEmailBridge(db).notify(payload.update, payload.context)


@router.post("/creator/qa-alert")
async def creator_qa_alert(
    payload: QAAlertRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    return await CreatorEmailBridge(db).qa_alert(payload.regressions, payload.results)


@router.post("/creator/monitoring-digest")
async def creator_monitoring_digest(
    payload: MonitoringDigestRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    return await CreatorEmailBridge(db).monitoring_digest(payload.items)


@router.post("/creator/approval-request")
async def creator_approval_request(
    payload: CreatorApprovalRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Raise a signed Creator challenge; email is the carrier, not the authority."""
    return await CreatorEmailBridge(db).approval_request(
        payload.action_type,
        payload.summary,
        target_ref=payload.target_ref,
        consequences=payload.consequences,
        risk_level=payload.risk_level,
        reason=payload.reason,
    )


def _builtin_cases() -> List[BenchmarkCase]:
    gateway = EgressGateway(resolver=lambda _: ["93.184.216.34"])
    return [
        BenchmarkCase(
            "ssrf_internal_blocked",
            1.0,
            lambda: 1.0 if not gateway.assess("http://127.0.0.1/latest/meta-data").allowed else 0.0,
        ),
        BenchmarkCase(
            "public_host_allowed",
            1.0,
            lambda: 1.0 if gateway.assess("https://example.com/page").allowed else 0.0,
        ),
        BenchmarkCase(
            "confidence_labelling",
            1.0,
            lambda: 1.0
            if (
                label_for_confidence(0.2) == "unverified"
                and label_for_confidence(0.55) == "provisional"
                and label_for_confidence(0.9) == "verified"
            )
            else 0.0,
        ),
        BenchmarkCase(
            "regression_gate_detects_drop",
            1.0,
            lambda: 1.0
            if not BenchmarkSuite.regression_gate({"x": 0.9}, {"x": 0.7}, 0.05)[0]
            else 0.0,
        ),
    ]


@router.post("/qa/run")
async def run_qa(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """Run the scored internet QA suite, compare with the last run and persist."""
    results = await BenchmarkSuite(_builtin_cases()).run()
    current = {item["benchmark"]: item["score"] for item in results}
    previous_rows = await db.execute(
        select(IICSBenchmarkResult)
        .order_by(IICSBenchmarkResult.run_at.desc())
        .limit(1000)
    )
    baseline: Dict[str, float] = {}
    for row in previous_rows.scalars().all():
        name = str(row.benchmark)
        if name not in baseline:
            baseline[name] = float(row.score)
    allowed, regressions = (
        BenchmarkSuite.regression_gate(baseline, current) if baseline else (True, [])
    )
    for item in results:
        db.add(
            IICSBenchmarkResult(
                benchmark=item["benchmark"],
                score=item["score"],
                threshold=item["threshold"],
                passed=item["passed"],
                evidence=item["evidence"],
            )
        )
    await db.commit()
    return {
        "results": results,
        "gate_allowed": allowed,
        "regressions": regressions,
        "previous_baseline": baseline,
    }


@router.get("/qa/results")
async def list_qa_results(
    limit: int = 100, db: AsyncSession = Depends(get_db_session)
) -> List[Dict[str, Any]]:
    """Return persisted benchmark runs (evidence for the QA gate)."""
    result = await db.execute(
        select(IICSBenchmarkResult)
        .order_by(IICSBenchmarkResult.run_at.desc())
        .limit(min(limit, 1000))
    )
    return [
        {
            "benchmark": row.benchmark,
            "score": float(row.score),
            "threshold": float(row.threshold),
            "passed": bool(row.passed),
            "evidence": dict(row.evidence or {}),
            "run_at": row.run_at.isoformat() if row.run_at else None,
        }
        for row in result.scalars().all()
    ]
