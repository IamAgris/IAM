"""Document 26 (OD-45): HBI routes.

Governance refusals are structured responses; no route bypasses purpose and
scope checks. Predictions are withheld until validated (A8).
"""

from fastapi import APIRouter, Body, Depends, HTTPException
from typing import Any, AsyncIterator, Dict, Optional

from app.core.database import get_db_session
from app.services.hbi import GovernanceRefusal, HBIService
from app.services.hbi.http_fetcher import fetch as http_fetch
from app.services.hbi.schemas import (
    AnalogyEvaluationRequest,
    AnalogyRequest,
    AnalysisRequest,
    BacktestRequest,
    ChronologyInput,
    CorpusIngestRequest,
    CorpusRestrictionRequest,
    CorpusReviewRequest,
    CrossDisciplinaryRequest,
    DPIASignoffRequest,
    DeprecateRequest,
    DualUseRequest,
    ForecastRequest,
    GraphEdgeRequest,
    GraphNodeRequest,
    KnowledgeRecordInput,
    ManipulationRequest,
    ModuleAnalysisRequest,
    MultilingualIngestRequest,
    OversightRequest,
    PredictionEvaluationRequest,
    PredictionRequest,
    ResearchDocumentInput,
    ResearchRequest,
    RevisionRequest,
    SourceCalibrationRequest,
    Scope,
    SourceRegisterRequest,
    TemporalRequest,
    TheoryComparisonRequest,
)
from app.services.hbi.sources import SourceNotAuthorised

router = APIRouter(prefix="/api/v1/hbi", tags=["human-behaviour-intelligence"])


async def _service(db=Depends(get_db_session)) -> AsyncIterator[HBIService]:
    """Commit knowledge and audit writes only on a successful request."""
    service = HBIService(db)
    try:
        yield service
        await db.commit()
    except Exception:
        await db.rollback()
        raise


def _translate(error: GovernanceRefusal) -> HTTPException:
    status = 403 if error.code == "PURPOSE_MISMATCH" else 422
    return HTTPException(status_code=status, detail={"code": error.code, "reason": error.reason})


@router.get("/status")
async def status():
    return HBIService().status()


@router.post("/knowledge/records")
async def add_record(request: KnowledgeRecordInput, service: HBIService = Depends(_service)):
    """Store a graded epistemic object with provenance and epistemic discipline."""
    try:
        return await service.add_record(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/knowledge/ingest")
async def ingest(request: ResearchDocumentInput, service: HBIService = Depends(_service)):
    """Ingest a licensed document; weak or unlicensed material is quarantined."""
    return await service.ingest(request)


@router.get("/knowledge/records")
async def search_records(
    scope: Optional[Scope] = None,
    tier: Optional[str] = None,
    epistemic_type: Optional[str] = None,
    evidence_class: Optional[str] = None,
    keyword: Optional[str] = None,
    limit: int = 50,
    service: HBIService = Depends(_service),
):
    """Retrieve records; tier and scope filters are applied before search."""
    return await service.search_records(
        scope=scope.value if scope else None,
        tier=tier,
        epistemic_type=epistemic_type,
        evidence_class=evidence_class,
        keyword=keyword,
        limit=limit,
    )


@router.get("/knowledge/quarantine")
async def quarantine(service: HBIService = Depends(_service)):
    """List quarantined material; it is never promoted silently."""
    return service.quarantine()


@router.post("/analysis")
async def analyse(request: AnalysisRequest, service: HBIService = Depends(_service)):
    try:
        return await service.analyse(request)
    except GovernanceRefusal as error:
        raise _translate(error)


@router.post("/research/search")
async def research(request: ResearchRequest, service: HBIService = Depends(_service)):
    try:
        return await service.research(request)
    except GovernanceRefusal as error:
        raise _translate(error)


@router.post("/predictions")
async def predict(request: PredictionRequest, service: HBIService = Depends(_service)):
    """Phase 1 returns a structured A8 refusal, never an unverified forecast."""
    try:
        return await service.predict(request)
    except GovernanceRefusal as error:
        raise _translate(error)


@router.get("/gaps")
async def gaps(query: str = "", service: HBIService = Depends(_service)):
    return await service.gaps(query)


@router.post("/contradictions/detect")
async def contradictions(service: HBIService = Depends(_service)):
    return await service.detect_contradictions()


@router.post("/chronology/resolve")
async def chronology(request: ChronologyInput, service: HBIService = Depends(_service)):
    return service.resolve_chronology(request)


@router.get("/modules")
async def list_modules(service: HBIService = Depends(_service)):
    return service.list_modules()


@router.post("/modules/{module_id}/analyse")
async def analyse_module(module_id: int, request: ModuleAnalysisRequest,
                         service: HBIService = Depends(_service)):
    try:
        return await service.analyse_module(module_id, request)
    except GovernanceRefusal as error:
        raise _translate(error)


@router.post("/temporal")
async def temporal(request: TemporalRequest, service: HBIService = Depends(_service)):
    try:
        return await service.temporal(request)
    except GovernanceRefusal as error:
        raise _translate(error)


@router.get("/sources")
async def list_sources(service: HBIService = Depends(_service)):
    """List explicitly authorised public sources."""
    return service.list_sources()


@router.post("/sources/register")
async def register_source(request: SourceRegisterRequest, service: HBIService = Depends(_service)):
    """Register a domain with a licence and permitted purpose before fetching."""
    try:
        return service.register_source(request)
    except SourceNotAuthorised as error:
        raise HTTPException(status_code=422, detail=error.reason)


@router.post("/sources/fetch")
async def fetch_source(url: str, service: HBIService = Depends(_service)):
    """Fetch from an allowlisted source via the robots-respecting transport."""
    try:
        return service.fetch_source(url, http_fetch)
    except SourceNotAuthorised as error:
        raise HTTPException(status_code=403, detail=error.reason)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.post("/backtest")
async def backtest(request: BacktestRequest, service: HBIService = Depends(_service)):
    """Leakage-free retrospective forecast with scoring."""
    return service.backtest(request)


@router.post("/models/validate")
async def validate_model(model_id: str, request: BacktestRequest,
                         service: HBIService = Depends(_service)):
    """Validate a model against backtests before permitting emission."""
    from app.services.hbi.prediction import HistoricalCase
    cases = [
        HistoricalCase(
            case_id=str(item.get("case_id", "")),
            cutoff_year=int(item["cutoff_year"]),
            outcome_year=int(item["outcome_year"]),
            features={str(k): float(v) for k, v in (item.get("features") or {}).items()},
            outcome=int(item["outcome"]),
        )
        for item in request.cases
    ]
    return service.validate_model(model_id, cases)


@router.post("/research/self-directed")
async def self_directed_research(query: str, purpose: str,
                                 service: HBIService = Depends(_service)):
    """A1: turn knowledge gaps into candidate research directions."""
    try:
        return await service.self_directed_research(query, purpose)
    except GovernanceRefusal as error:
        raise _translate(error)


@router.post("/theories/compare")
async def compare_theories(request: TheoryComparisonRequest,
                           service: HBIService = Depends(_service)):
    """A2: compare competing theories on held-out cases."""
    return service.compare_theories(request)


@router.post("/hypotheses/generate")
async def generate_hypotheses(purpose: str, service: HBIService = Depends(_service)):
    """A3: generate falsifiable hypotheses, stored as hypothesis records."""
    try:
        return await service.generate_hypotheses(purpose)
    except GovernanceRefusal as error:
        raise _translate(error)


@router.post("/history/analogy")
async def analogy(request: AnalogyRequest, service: HBIService = Depends(_service)):
    """A4: score a historical analogy and allow a weak/misleading verdict."""
    return service.analogy(request)


@router.post("/predictions/evaluate")
async def evaluate_prediction(request: PredictionEvaluationRequest,
                              service: HBIService = Depends(_service)):
    """A5: diagnose prediction error without rewriting the original."""
    return service.evaluate_prediction(request)


@router.post("/history/graph/nodes")
async def add_graph_node(request: GraphNodeRequest, service: HBIService = Depends(_service)):
    return await service.add_graph_node(request)


@router.post("/history/graph/edges")
async def add_graph_edge(request: GraphEdgeRequest, service: HBIService = Depends(_service)):
    try:
        return await service.add_graph_edge(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/history/graph/query")
async def query_graph(node_type: Optional[str] = None, period: Optional[str] = None,
                      region: Optional[str] = None, relation: Optional[str] = None,
                      keyword: Optional[str] = None, limit: int = 50,
                      service: HBIService = Depends(_service)):
    return service.query_graph(node_type=node_type, period=period, region=region,
                               relation=relation, keyword=keyword, limit=limit)


@router.get("/history/graph/{node_ref}/expand")
async def expand_graph(node_ref: str, depth: int = 1,
                       service: HBIService = Depends(_service)):
    try:
        return service.expand_graph(node_ref, depth)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/history/timeline/ingest")
async def ingest_timeline(request: ChronologyInput, service: HBIService = Depends(_service)):
    """Materialise E13 chronology output into the historical knowledge graph."""
    return await service.ingest_timeline(request)


@router.post("/reasoning/cross-disciplinary")
async def cross_disciplinary(request: CrossDisciplinaryRequest,
                             service: HBIService = Depends(_service)):
    """A6: fuse graded claims from multiple disciplines without dominance."""
    return service.cross_disciplinary(request)


@router.post("/knowledge/revise")
async def revise(request: RevisionRequest, service: HBIService = Depends(_service)):
    """A7: supersede a record with a new version, preserving the old one."""
    try:
        return await service.revise(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/knowledge/deprecate")
async def deprecate(request: DeprecateRequest, service: HBIService = Depends(_service)):
    try:
        return service.deprecate(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/knowledge/{record_ref}/lineage")
async def lineage(record_ref: str, service: HBIService = Depends(_service)):
    return service.lineage(record_ref)


@router.post("/uncertainty/assess")
async def uncertainty(query: str, purpose: str, service: HBIService = Depends(_service)):
    """A8: decide whether the question is reliably predictable at all."""
    try:
        return service.uncertainty_assessment(query, purpose)
    except GovernanceRefusal as error:
        raise _translate(error)


@router.post("/manipulation/analyse")
async def manipulation(request: ManipulationRequest, service: HBIService = Depends(_service)):
    """Defensive recognition of manipulation patterns in supplied text."""
    return service.analyse_manipulation(request)


@router.post("/behaviour/forecast")
async def forecast(request: ForecastRequest, service: HBIService = Depends(_service)):
    """Module 13: probability distribution over scenarios, gated by A8 and validation."""
    try:
        return await service.forecast(request)
    except GovernanceRefusal as error:
        raise _translate(error)


@router.post("/history/modules/{module_id}/analyse")
async def historical_module(module_id: int, question: str, purpose: str = "historical_research",
                            service: HBIService = Depends(_service)):
    """Modules 16–23: historical analysis with preserved contested evidence."""
    try:
        return await service.historical_module(module_id, question, purpose)
    except GovernanceRefusal as error:
        raise _translate(error)


@router.post("/history/analogy/evaluate")
async def evaluate_analogies(request: AnalogyEvaluationRequest,
                             service: HBIService = Depends(_service)):
    """Measure whether strong analogies actually predicted documented outcomes."""
    return service.evaluate_analogies(request)


@router.get("/causal/assess")
async def causal(question: str, service: HBIService = Depends(_service)):
    """Return whether causal language is permitted for this question."""
    return service.causal(question)


@router.post("/history/civilisation/analyse")
async def civilisation(question: str, purpose: str = "historical_research",
                       service: HBIService = Depends(_service)):
    """Module 27: multi-factor development and decline analysis."""
    try:
        return await service.civilisation(question, purpose)
    except GovernanceRefusal as error:
        raise _translate(error)


@router.post("/knowledge/ingest/multilingual")
async def ingest_multilingual(request: MultilingualIngestRequest,
                              service: HBIService = Depends(_service)):
    """Batch ingestion with language/script detection and duplicate screening."""
    return await service.ingest_multilingual(request)


@router.post("/acceptance/run")
async def run_acceptance(service: HBIService = Depends(_service)):
    """Run all §11.7 acceptance gates; a failed gate blocks promotion."""
    return await service.run_acceptance()


@router.post("/knowledge/corpus/ingest")
async def ingest_corpus(request: CorpusIngestRequest, service: HBIService = Depends(_service)):
    """Ingest a local corpus; every source must first pass the fail-closed gate."""
    try:
        return await service.ingest_corpus(request)
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/knowledge/corpus/review")
async def review_corpus_source(request: CorpusReviewRequest,
                               service: HBIService = Depends(_service)):
    """Approve, reject or quarantine a source with an auditable reason."""
    return service.review_corpus_source(request)


@router.get("/knowledge/corpus/state")
async def corpus_state(service: HBIService = Depends(_service)):
    """Overall corpus state: not_validated, validated or restricted."""
    return service.corpus_state()


@router.get("/knowledge/corpus/audit")
async def corpus_audit(service: HBIService = Depends(_service)):
    """Who approved a source, when, and which rules were applied."""
    return service.corpus_audit()


@router.post("/knowledge/corpus/restrict")
async def restrict_corpus_source(request: CorpusRestrictionRequest,
                                 service: HBIService = Depends(_service)):
    """Suspend a previously accepted source and record the reason."""
    return service.restrict_corpus_source(request)


@router.post("/models/calibrate-sources")
async def calibrate_sources(request: SourceCalibrationRequest,
                            service: HBIService = Depends(_service)):
    """Learn empirical source reliability from labelled outcomes."""
    return service.calibrate_sources(request)


@router.get("/backtest/library")
async def backtest_library(service: HBIService = Depends(_service)):
    """Inspect the versioned backtest case library and its provenance status."""
    return service.backtest_library()


@router.post("/models/validate-library")
async def validate_library(model_id: str = "ensemble",
                           service: HBIService = Depends(_service)):
    """Validate a model on the illustrative fixture library."""
    return service.validate_on_library(model_id)


@router.post("/governance/dual-use/review")
async def dual_use_review(request: DualUseRequest, service: HBIService = Depends(_service)):
    """Classify a capability before deployment; prohibited capabilities are blocked."""
    return service.dual_use_review(request)


@router.get("/governance/dpia")
async def dpia(service: HBIService = Depends(_service)):
    """Technical DPIA input for an authorised reviewer; not legal clearance."""
    return service.dpia()


@router.post("/governance/oversight/check")
async def oversight(request: OversightRequest, service: HBIService = Depends(_service)):
    """Consequential decisions always require an accountable human reviewer."""
    return service.oversight(request)


@router.post("/governance/dpia/signoff")
async def sign_off_dpia(request: DPIASignoffRequest, service: HBIService = Depends(_service)):
    """Record an authorised reviewer's DPIA decision."""
    try:
        return await service.sign_off_dpia(request)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.post("/governance/deployment/readiness")
async def deployment_readiness(config: Dict[str, Any] = Body(default_factory=dict),
                               service: HBIService = Depends(_service)):
    """Go/no-go check for production activation; IAM cannot self-approve."""
    return await service.deployment_readiness(config)


@router.get("/validation/cases")
async def validation_cases(service: HBIService = Depends(_service)):
    """Derive leakage-safe backtest cases from graded, dated records only."""
    return service.validation_cases()


@router.get("/validation/bias")
async def validation_bias(service: HBIService = Depends(_service)):
    """Measure performance disparities across recorded populations."""
    return service.validation_bias()


@router.get("/validation/report")
async def validation_report(model_id: str = "ensemble",
                            service: HBIService = Depends(_service)):
    """Validation verdict; refuses to claim validation without real evidence."""
    return service.validation_report(model_id)


@router.get("/validation/corpus-readiness")
async def corpus_readiness(service: HBIService = Depends(_service)):
    """Report whether licensed corpus evidence — not fixtures — is available."""
    return service.corpus_readiness()


@router.get("/lifecycle/drift")
async def drift(service: HBIService = Depends(_service)):
    """Detect confidence drift across dated periods."""
    return service.drift_report()


@router.get("/lifecycle/re-evaluation")
async def re_evaluation(service: HBIService = Depends(_service)):
    """List models needing periodic re-evaluation."""
    return service.re_evaluation_plan()


@router.post("/lifecycle/rollback-drill")
async def rollback_drill(model_id: str = "ensemble",
                         service: HBIService = Depends(_service)):
    """Exercise rollback without promoting an unvalidated model."""
    return service.rollback_drill(model_id)
