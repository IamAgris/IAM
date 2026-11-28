"""Document 26 (OD-45): HBI service facade used by API routes."""

from typing import Any, Dict, List, Optional

from app.services.hbi import (
    acceptance, advanced, backtest_library, calibration, civilisation,
    contradictions, deployment, dual_use, dpia, forecasting, gaps, historical,
    evaluation_module, lifecycle, manipulation, modules, oversight, temporal,
    uncertainty, validation,
)
from app.services.hbi.corpus import ingest_corpus as load_corpus
from app.core.config import settings
from app.services.hbi.corpus_gate import CorpusGovernance
from app.services.hbi.http_fetcher import fetch_json as fetch_public_json
from app.services.hbi.open_sources import fetch_documents, list_adapters
from app.services.hbi.permission_engine import PermissionEngine
from app.services.hbi.research_ecosystem import ResearchEcosystem
from app.services.hbi.research_lab import ResearchLab
from app.services.hbi.synthetic import build_scenarios, to_records as synthetic_records
from app.services.hbi.translation import TranslationService
from app.services.hbi.chronology import resolve as resolve_chronology
from app.services.hbi.cross_disciplinary import fuse as fuse_disciplines
from app.services.hbi.evolution import deprecate as deprecate_record, lineage as record_lineage, revise as revise_record
from app.services.hbi.hkg import HistoricalKnowledgeGraph
from app.services.hbi.core import GovernanceRefusal, HBICore
from app.services.hbi.ingestion import ResearchIngestionService
from app.services.hbi.knowledge import KnowledgeStore
from app.services.hbi.prediction import (
    BetaBinomialModel,
    EnsembleForecaster,
    EvidenceForecaster,
    HistoricalCase,
    LogisticModel,
    backtest as run_backtest,
)
from app.services.hbi.schemas import (
    AnalogyEvaluationRequest,
    AnalogyRequest,
    AnalysisRequest,
    BacktestRequest,
    CorpusIngestRequest,
    CorpusRestrictionRequest,
    CorpusReviewRequest,
    DPIASignoffRequest,
    LegalContextVerificationRequest,
    PartnershipRequest,
    ContributionRequest,
    FederatedApprovalRequest,
    FederatedRequest,
    LabProjectRequest,
    TargetVerificationRequest,
    TrainingApprovalRequest,
    TrainingRequest,
    TransformationRequest,
    TranslationRequest,
    StudyCreateRequest,
    StudyResponseRequest,
    ForecastRequest,
    ChronologyInput,
    CrossDisciplinaryRequest,
    DeprecateRequest,
    DualUseRequest,
    GraphEdgeRequest,
    GraphNodeRequest,
    KnowledgeRecordInput,
    ManipulationRequest,
    MultilingualIngestRequest,
    MultilingualSemanticsRequest,
    ModuleAnalysisRequest,
    OpenSourceIngestRequest,
    OversightRequest,
    ParticipantConsentRequest,
    ParticipantWithdrawalRequest,
    PredictionEvaluationRequest,
    PredictionRequest,
    ResearchDocumentInput,
    ResearchRequest,
    RevisionRequest,
    SourceCalibrationRequest,
    SourceRegisterRequest,
    SyntheticStudyRequest,
    TemporalRequest,
    TheoryComparisonRequest,
)
from app.services.hbi.sources import AuthorisedSource, LiveSourceRegistry
from app.services.hbi.prediction import PredictionService
from app.services.model_inference import InferenceService


class HBIService:
    """Facade: governed knowledge, ingestion, modules and temporal analysis."""

    def __init__(self, db_session: Optional[Any] = None, local_signoff_file: bool = True):
        self.store = KnowledgeStore(db_session)
        self.local_signoff_file = local_signoff_file
        self.core = HBICore(self.store)
        self.ingestion = ResearchIngestionService(self.store)
        self.sources = LiveSourceRegistry()  # type: ignore[no-untyped-call]
        self.graph = HistoricalKnowledgeGraph(db_session)
        self.corpus_governance = CorpusGovernance()  # type: ignore[no-untyped-call]
        self.permission_engine = PermissionEngine(self.corpus_governance)
        self.ecosystem = ResearchEcosystem(self.corpus_governance, self.permission_engine)
        self.translation = TranslationService(inference=InferenceService())
        self.lab = ResearchLab()
        self.dpia_signoffs: List[Dict[str, Any]] = []
        self.predictor = PredictionService()
        self.predictor.register("baseline", EvidenceForecaster())
        self.predictor.register("beta_binomial", BetaBinomialModel())
        self.predictor.register("ensemble", EnsembleForecaster())
        self.predictor.register("logistic", LogisticModel())

    async def ensure_loaded(self) -> List[Dict[str, Any]]:
        """Hydrate persisted records once, then return the cache."""
        if self.store.db is not None and not self.store.hydrated:
            await self.store.hydrate()
        return self.store.all()

    async def add_record(self, payload: KnowledgeRecordInput) -> Dict[str, Any]:
        return await self.store.add(payload)

    async def ingest(self, payload: ResearchDocumentInput) -> Dict[str, Any]:
        return await self.ingestion.ingest(payload)

    async def search_records(self, **filters) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        records = await self.ensure_loaded()
        filtered = []
        for record in records:
            if filters.get("scope") and record["scope"] != filters["scope"]:
                continue
            if filters.get("tier") and record["tier"] != filters["tier"]:
                continue
            if filters.get("epistemic_type") and record["epistemic_type"] != filters["epistemic_type"]:
                continue
            if filters.get("evidence_class") and record["evidence_class"] != filters["evidence_class"]:
                continue
            if filters.get("keyword") and filters["keyword"].lower() not in record["claim"].lower():
                continue
            filtered.append(record)
        return {"count": len(filtered),
                "records": filtered[:filters.get("limit", 50)]}

    async def analyse(self, payload: AnalysisRequest) -> Dict[str, Any]:
        return self.core.analyse(payload, await self.ensure_loaded())

    async def research(self, payload: ResearchRequest) -> Dict[str, Any]:
        return self.core.research(payload, await self.ensure_loaded())

    async def predict(self, payload: PredictionRequest) -> Dict[str, Any]:
        """Emit only from a validated model; otherwise return an A8 refusal."""
        self.core.check_governance(payload.purpose, payload.scope.value)
        records = await self.ensure_loaded()
        gaps_result = gaps.detect(records, payload.question)
        model_id = payload.model_id or "baseline"
        a8 = uncertainty.assess(
            records, gaps_result,
            contradictions.detect([{"record_id": r["record_ref"], "claim": r["claim"]} for r in records]),
            payload.scope.value,
            self.predictor.validation.get(model_id),  # type: ignore[arg-type]
        )
        if a8.get("refusal"):
            self.core._audit("prediction", payload.purpose, payload.scope.value,
                             "refused", {"target": payload.target, "a8": a8["verdict"]})
            return {
                "prediction_id": None, "target": payload.target,
                "scope": payload.scope.value, "time_horizon": payload.time_horizon,
                "probability": {}, "confidence": 0.0,
                "uncertainty_assessment": a8, "refusal": a8["refusal"],
                "gaps": gaps_result["gaps"],
            }
        result = self.predictor.predict(
            model_id, payload.features, payload.purpose, payload.scope.value
        )
        if result.get("refusal"):
            result.update({
                "prediction_id": None,
                "target": payload.target,
                "scope": payload.scope.value,
                "time_horizon": payload.time_horizon,
                "gaps": gaps_result["gaps"],
            })
            self.core._audit("prediction", payload.purpose, payload.scope.value,
                             "refused", {"target": payload.target})
            return result
        self.core._audit("prediction", payload.purpose, payload.scope.value,
                         "emitted", {"target": payload.target, "model_id": model_id})
        return result

    def validate_model(self, model_id: str, cases: List[HistoricalCase]) -> Dict[str, Any]:
        return self.predictor.validate(model_id, cases)

    def backtest(self, payload: BacktestRequest) -> Dict[str, Any]:
        cases = []
        for item in payload.cases:
            cases.append(HistoricalCase(
                case_id=str(item.get("case_id", "")),
                cutoff_year=int(item["cutoff_year"]),
                outcome_year=int(item["outcome_year"]),
                features={str(k): float(v) for k, v in (item.get("features") or {}).items()},
                outcome=int(item["outcome"]),
                target=str(item.get("target", "aggregate_event")),
            ))
        return run_backtest(cases)

    def register_source(self, payload: SourceRegisterRequest) -> Dict[str, Any]:
        self.sources.register(AuthorisedSource(
            source_id=payload.source_id,
            domain=payload.domain,
            source_type=payload.source_type,
            licence=payload.licence,
            permitted_purpose=payload.permitted_purpose,
            require_robots=payload.require_robots,
        ))
        return {"registered": payload.source_id}

    def list_sources(self) -> Dict[str, Any]:
        return {"count": len(self.sources.sources), "sources": self.sources.list()}

    def fetch_source(self, url: str, fetcher=None) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        """Fetch only from allowlisted domains with a licence and purpose."""
        return self.sources.fetch(url, fetcher)

    async def gaps(self, query: str = "") -> Dict[str, Any]:
        return gaps.detect(await self.ensure_loaded(), query)

    async def detect_contradictions(self) -> Dict[str, Any]:
        return contradictions.detect([{"record_id": r["record_ref"], "claim": r["claim"]}
                                      for r in await self.ensure_loaded()])

    def resolve_chronology(self, payload: ChronologyInput) -> Dict[str, Any]:
        return resolve_chronology(payload.events, payload.uncertain_periods, payload.conflicting_accounts)

    def list_modules(self) -> Dict[str, Any]:
        return modules.list_modules()

    async def analyse_module(self, module_id: int, payload: ModuleAnalysisRequest) -> Dict[str, Any]:
        self.core.check_governance(payload.purpose, payload.scope.value)
        records = await self.ensure_loaded()
        if module_id == 15:
            result = evaluation_module.analyse(records, self.predictor)
        else:
            result = modules.analyse(module_id, payload.question, records)
        self.core._audit("module_analysis", payload.purpose, payload.scope.value,
                         result.get("status", "unknown"), {"module_id": module_id})
        return result

    async def temporal(self, payload: TemporalRequest) -> Dict[str, Any]:
        self.core.check_governance(payload.purpose, "aggregate")
        return temporal.analyse(await self.ensure_loaded(), payload.question,
                                payload.context_key, payload.limit)

    def quarantine(self) -> Dict[str, Any]:
        return {"count": len(self.store.quarantine), "items": self.store.quarantine}

    async def self_directed_research(self, query: str, purpose: str) -> Dict[str, Any]:
        """A1: gaps become bounded research candidates, never invented findings."""
        self.core.check_governance(purpose, "aggregate")
        result = advanced.research_from_gaps(gaps.detect(await self.ensure_loaded(), query))
        self.core._audit("self_directed_research", purpose, "aggregate", "completed", {"query": query})
        return result

    def compare_theories(self, payload: TheoryComparisonRequest) -> Dict[str, Any]:
        return advanced.compare_theories(payload.theories, payload.cases)

    async def generate_hypotheses(self, purpose: str) -> Dict[str, Any]:
        """A3: generate falsifiable hypotheses from gaps and contradictions."""
        self.core.check_governance(purpose, "aggregate")
        records = await self.ensure_loaded()
        candidates = advanced.generate_hypotheses(
            records,
            gaps.detect(records),
            contradictions.detect([{"record_id": r["record_ref"], "claim": r["claim"]} for r in records]),
        )
        stored = []
        for candidate in candidates:
            record = await self.store.add(KnowledgeRecordInput(
                claim=candidate["claim"],
                epistemic_type="hypothesis",  # type: ignore[arg-type]
                alternatives=["not_supported_until_tested"],
                falsifier=candidate["falsifier"],
                confidence=0.0,
                module_ids=[15],
            ))
            stored.append({**candidate, "record_ref": record["record_ref"]})
        self.core._audit("hypothesis_generation", purpose, "aggregate", "completed",
                         {"count": len(stored)})
        return {"count": len(stored), "hypotheses": stored}

    def analogy(self, payload: AnalogyRequest) -> Dict[str, Any]:
        return advanced.analogy(payload.current, payload.precedent)

    def evaluate_prediction(self, payload: PredictionEvaluationRequest) -> Dict[str, Any]:
        """A5: diagnose error without rewriting the original prediction."""
        return advanced.diagnose_prediction(payload.prediction, payload.outcome)

    async def add_graph_node(self, payload: GraphNodeRequest) -> Dict[str, Any]:
        return await self.graph.add_node(
            node_ref=payload.node_ref, node_type=payload.node_type, label=payload.label,
            period=payload.period, region=payload.region, date_value=payload.date_value,
            properties=payload.properties, evidence_class=payload.evidence_class,
        )

    async def add_graph_edge(self, payload: GraphEdgeRequest) -> Dict[str, Any]:
        return await self.graph.add_edge(
            from_ref=payload.from_ref, to_ref=payload.to_ref, relation=payload.relation,
            confidence=payload.confidence, evidence_class=payload.evidence_class,
        )

    def query_graph(self, **filters) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        return self.graph.query(**filters)

    def expand_graph(self, node_ref: str, depth: int = 1) -> Dict[str, Any]:
        return self.graph.expand(node_ref, depth)

    async def ingest_timeline(self, payload: ChronologyInput) -> Dict[str, Any]:
        resolved = self.resolve_chronology(payload)
        return await self.graph.ingest_timeline(resolved)

    def cross_disciplinary(self, payload: CrossDisciplinaryRequest) -> Dict[str, Any]:
        return fuse_disciplines(payload.question, payload.claims_by_discipline,
                                payload.calibration_weights)

    async def revise(self, payload: RevisionRequest) -> Dict[str, Any]:
        """A7: create a new version and preserve the old one."""
        result = await revise_record(self.store, payload.old_ref, payload.payload, payload.rationale)
        self.core._audit("revision", "knowledge_evolution", "aggregate", "completed",
                         {"old_ref": payload.old_ref, "new_ref": result["new_ref"]})
        return result

    def deprecate(self, payload: DeprecateRequest) -> Dict[str, Any]:
        return deprecate_record(self.store, payload.record_ref, payload.reason)

    def lineage(self, record_ref: str) -> Dict[str, Any]:
        return record_lineage(self.store, record_ref)

    def uncertainty_assessment(self, query: str, purpose: str) -> Dict[str, Any]:
        """A8: explicit predictability verdict for a question."""
        self.core.check_governance(purpose, "aggregate")
        records = self.store.all()
        result = uncertainty.assess(
            records, gaps.detect(records, query),
            contradictions.detect([{"record_id": r["record_ref"], "claim": r["claim"]} for r in records]),
        )
        self.core._audit("uncertainty_assessment", purpose, "aggregate", result["verdict"], {"query": query})
        return result

    def analyse_manipulation(self, payload: ManipulationRequest) -> Dict[str, Any]:
        """Defensive recognition only; no influence content is generated."""
        if len(payload.texts) == 1:
            return manipulation.analyse(payload.texts[0])
        return manipulation.analyse_discussion(payload.texts)

    async def forecast(self, payload: ForecastRequest) -> Dict[str, Any]:
        """Module 13: emit only after A8 approval and model validation."""
        self.core.check_governance(payload.purpose, payload.scope.value)
        prediction_request = PredictionRequest(
            question=payload.question, target=payload.target, purpose=payload.purpose,
            scope=payload.scope, time_horizon=payload.time_horizon,
            context_refs=payload.context_refs, model_id=payload.model_id or "ensemble",
            features=payload.features,
        )
        result = await self.predict(prediction_request)
        return forecasting.forecast(
            {"target": payload.target, "time_horizon": payload.time_horizon}, result
        )

    async def historical_module(self, module_id: int, question: str,
                                purpose: str = "historical_research") -> Dict[str, Any]:
        """Modules 16–23: historical analysis with preserved evidence classes."""
        self.core.check_governance(purpose, "aggregate")
        result = historical.analyse(module_id, question, await self.ensure_loaded(), self.graph)
        self.core._audit("historical_module", purpose, "aggregate",
                         result.get("status", "unknown"), {"module_id": module_id})
        return result

    def evaluate_analogies(self, payload: AnalogyEvaluationRequest) -> Dict[str, Any]:
        return advanced.evaluate_analogies(payload.current, payload.precedents, payload.cases)

    def causal(self, question: str) -> Dict[str, Any]:
        from app.services.hbi.causal import causal_assessment
        return causal_assessment(question, self.store.all())

    async def civilisation(self, question: str, purpose: str = "historical_research") -> Dict[str, Any]:
        """Module 27: multi-factor civilisational analysis."""
        self.core.check_governance(purpose, "aggregate")
        result = civilisation.analyse(question, await self.ensure_loaded(), self.graph)
        self.core._audit("civilisation", purpose, "aggregate", "completed", {"question": question})
        return result

    async def ingest_multilingual(self, payload: MultilingualIngestRequest) -> Dict[str, Any]:
        return await self.ingestion.ingest_multilingual(payload.documents)

    async def run_acceptance(self) -> Dict[str, Any]:
        return await acceptance.run_acceptance(self)

    async def ingest_corpus(self, payload: CorpusIngestRequest) -> Dict[str, Any]:
        return await load_corpus(self, payload.manifest_path, payload.root)

    def review_corpus_source(self, payload: CorpusReviewRequest) -> Dict[str, Any]:
        result = self.corpus_governance.review(
            payload.manifest, payload.intended_purpose,
            payload.approved_by, payload.model_training,
        )
        if result["decision"] == "approved":
            self.permission_engine.register_manifest(payload.manifest)
        return result

    def restrict_corpus_source(self, payload: CorpusRestrictionRequest) -> Dict[str, Any]:
        result = self.corpus_governance.restrict(payload.source_id, payload.reason)
        self.core._audit("corpus_restriction", "governance", "aggregate",
                         "restricted" if result["restricted"] else "failed",
                         {"source_id": payload.source_id})
        return result

    def corpus_state(self) -> Dict[str, Any]:
        return self.corpus_governance.state()

    def corpus_audit(self) -> Dict[str, Any]:
        return self.corpus_governance.audit_history()

    def drift_report(self) -> Dict[str, Any]:
        return lifecycle.drift_report(self.store.all())

    def re_evaluation_plan(self) -> Dict[str, Any]:
        return lifecycle.re_evaluation_plan(self)

    def rollback_drill(self, model_id: str = "ensemble") -> Dict[str, Any]:
        result = lifecycle.rollback_drill(self.predictor, model_id)
        self.core._audit("rollback_drill", "governance", "aggregate",
                         "passed" if result["passed"] else "failed", {"model_id": model_id})
        return result

    def calibrate_sources(self, payload: SourceCalibrationRequest) -> Dict[str, Any]:
        """Learn empirical source reliability; heuristics remain the fallback."""
        learned = calibration.learn_source_weights(payload.cases)
        self.ingestion.learned_weights = learned
        return {
            "source_weights": learned,
            "empirical_sources": [k for k, v in learned.items() if v["empirical"]],
            "note": "Empirical weights replace heuristic priors only where n >= 3.",
        }

    def backtest_library(self) -> Dict[str, Any]:
        return backtest_library.summary()

    def validate_on_library(self, model_id: str = "ensemble") -> Dict[str, Any]:
        """Validate a model on the shipped illustrative fixture library."""
        return self.predictor.validate(model_id, backtest_library.cases())

    def dual_use_review(self, payload: DualUseRequest) -> Dict[str, Any]:
        result = dual_use.review(payload.capability, payload.markers,
                                 payload.purpose, payload.scope.value)
        self.core._audit("dual_use_review", payload.purpose, payload.scope.value,
                         result["decision"], {"capability": payload.capability})
        return result

    def dpia(self) -> Dict[str, Any]:
        return dpia.build(self)

    def oversight(self, payload: OversightRequest) -> Dict[str, Any]:
        result = oversight.check(payload.decision_type, payload.evidence)
        self.core._audit("oversight_check", "human_oversight", "aggregate",
                         result["decision_type"], {"human_review_required": result["human_review_required"]})
        return result

    async def sign_off_dpia(self, payload: DPIASignoffRequest) -> Dict[str, Any]:
        record = dpia.sign_off(payload.reviewer, payload.decision, payload.basis)
        self.dpia_signoffs.append(record)
        if self.store.db is not None:
            from app.models.hbi import HBIDPIASignoff
            self.store.db.add(HBIDPIASignoff(
                reviewer=record["reviewer"], decision=record["decision"],
                basis=record["basis"], signed_at=record["signed_at"],
            ))
            await self.store.db.flush()
        self.core._audit("dpia_signoff", "governance", "aggregate",
                         payload.decision, {"reviewer": payload.reviewer})
        return record

    async def load_dpia_signoffs(self) -> List[Dict[str, Any]]:
        """Load durable sign-offs from PostgreSQL, or the local-first record."""
        if self.store.db is None:
            if self.local_signoff_file:
                import json
                from pathlib import Path
                path = Path(__file__).parent / "data" / "dpia_signoffs.json"
                if path.is_file():
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    return list(payload.get("records", []))
            return list(self.dpia_signoffs)
        from sqlalchemy import select
        from app.models.hbi import HBIDPIASignoff
        rows = (await self.store.db.execute(select(HBIDPIASignoff))).scalars().all()
        return [
            {
                "reviewer": row.reviewer, "decision": row.decision,
                "basis": row.basis, "signed_at": row.signed_at,
            }
            for row in rows
        ]

    async def deployment_readiness(self, config: Dict[str, Any] = None) -> Dict[str, Any]:  # type: ignore[assignment]
        return await deployment.readiness(self, config)

    def validation_cases(self) -> Dict[str, Any]:
        derived = validation.build_cases(self.store.all(), self.corpus_governance.approved_ids())
        return {k: v for k, v in derived.items() if k != "cases"} | {"case_count": len(derived["cases"])}

    def validation_bias(self) -> Dict[str, Any]:
        return validation.bias_report(self.store.all())

    def validation_report(self, model_id: str = "ensemble") -> Dict[str, Any]:
        return validation.report(self, model_id)

    def corpus_readiness(self) -> Dict[str, Any]:
        return validation.corpus_readiness(self.store.all())

    def request_training(self, payload: TrainingRequest) -> Dict[str, Any]:
        return self.permission_engine.request_training(payload)

    def approve_training(self, payload: TrainingApprovalRequest) -> Dict[str, Any]:
        result = self.permission_engine.approve_training(payload)
        self.core._audit("training_approval", payload.basis[:80], "aggregate",
                         result["decision"], {"source_id": payload.source_id})
        return result

    def training_approved(self) -> Dict[str, Any]:
        ids = sorted(self.permission_engine.training_approved_ids())
        return {"sources": ids, "count": len(ids), "note": "Pipeline 3 reads only these sources."}

    def add_partnership(self, payload: PartnershipRequest) -> Dict[str, Any]:
        return self.permission_engine.add_partnership(payload)

    def list_partnerships(self) -> Dict[str, Any]:
        return self.permission_engine.list_partnerships()

    def legal_context(self) -> Dict[str, Any]:
        return self.permission_engine.legal_context()

    def verify_legal_context(self, payload: LegalContextVerificationRequest) -> Dict[str, Any]:
        return self.permission_engine.verify_legal_context(payload)

    def permission_audit(self) -> Dict[str, Any]:
        return self.permission_engine.audit_history()

    def acquisition_channels(self) -> Dict[str, Any]:
        return self.ecosystem.channels()

    def discovery_targets(self) -> Dict[str, Any]:
        return self.ecosystem.discovery_targets()

    def verify_target(self, payload: TargetVerificationRequest) -> Dict[str, Any]:
        return self.ecosystem.verify_target(payload.name, payload.verified_by, payload.reference)

    def source_classification(self, source_id: str) -> Dict[str, Any]:
        return self.ecosystem.classify_source(source_id)

    def enforce(self, source_id: str, action: str) -> Dict[str, Any]:
        return self.ecosystem.enforce(source_id, action)

    @staticmethod
    def _payload_dict(payload: Any) -> Dict[str, Any]:
        _typed_result: dict[str, Any] = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
        return _typed_result

    def add_contribution(self, payload: ContributionRequest) -> Dict[str, Any]:
        return self.ecosystem.add_contribution(self._payload_dict(payload))

    def list_contributions(self) -> Dict[str, Any]:
        return self.ecosystem.list_contributions()

    def federated_request(self, payload: FederatedRequest) -> Dict[str, Any]:
        return self.ecosystem.federated_request(self._payload_dict(payload))

    def federated_approve(self, payload: FederatedApprovalRequest) -> Dict[str, Any]:
        return self.ecosystem.federated_approve(payload.institution, payload.approver, payload.reference)

    def lab_project(self, payload: LabProjectRequest) -> Dict[str, Any]:
        return self.ecosystem.lab_project(self._payload_dict(payload))

    def transform(self, payload: TransformationRequest) -> Dict[str, Any]:
        return self.ecosystem.transform(payload.source_ids, payload.output_type)

    def ecosystem_audit(self) -> Dict[str, Any]:
        return self.ecosystem.audit_history()

    async def translate(self, payload: TranslationRequest) -> Dict[str, Any]:
        """Local-first model translation; the original text is always preserved."""
        return await self.translation.translate(
            payload.text, payload.target_language, payload.source_language,
            model=payload.model or settings.iam_primary_model,
        )

    async def multilingual_semantics(self, payload: MultilingualSemanticsRequest) -> Dict[str, Any]:
        return await self.translation.multilingual_semantics(
            payload.text, payload.language, payload.region
        )

    def create_study(self, payload: StudyCreateRequest) -> Dict[str, Any]:
        return self.lab.create_study(payload)

    def record_consent(self, payload: ParticipantConsentRequest) -> Dict[str, Any]:
        return self.lab.record_consent(payload)

    def collect_response(self, payload: StudyResponseRequest) -> Dict[str, Any]:
        return self.lab.collect(payload)

    def withdraw_participant(self, payload: ParticipantWithdrawalRequest) -> Dict[str, Any]:
        return self.lab.withdraw(payload)

    def delete_study_responses(self, study_id: str, participant_ref: str) -> Dict[str, Any]:
        return self.lab.delete_responses(study_id, participant_ref)

    def study_report(self, study_id: str) -> Dict[str, Any]:
        return self.lab.report(study_id)

    def lab_audit(self) -> Dict[str, Any]:
        return self.lab.audit_history()

    def open_source_adapters(self) -> Dict[str, Any]:
        return list_adapters()

    async def ingest_open_source(self, payload: OpenSourceIngestRequest, fetcher=None) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        """Ingest metadata from a free official API through the normal gate."""
        result = await fetch_documents(
            payload.adapter, payload.query, fetcher or fetch_public_json, payload.limit
        )
        if result.get("error"):
            return result
        accepted = []
        for document in result["documents"]:
            ingested = await self.ingest(document)
            accepted.append({"source_id": document.source_id, "status": ingested.get("status", "ingested")})
        self.core._audit("open_source_ingest", "research", "aggregate", "completed",
                         {"adapter": payload.adapter, "documents": len(accepted)})
        return {
            "adapter": result["adapter"], "kind": result["kind"],
            "terms": result["terms"], "documents": result["count"],
            "accepted": accepted,
            "note": "Metadata only; per-item rights must be checked before retention or training.",
        }

    async def generate_synthetic(self, payload: SyntheticStudyRequest) -> Dict[str, Any]:
        """Generate IAM-owned scenarios from permitted material; no participants required."""
        self.core.check_governance(payload.purpose, "aggregate")
        claims = [r["claim"] for r in self.store.all()]
        scenarios = build_scenarios(claims, payload.count)
        records = []
        for record in synthetic_records(scenarios, payload.study_ref):
            stored = await self.store.add(record)
            records.append({"record_ref": stored["record_ref"], "claim": stored["claim"]})
        self.core._audit("synthetic_generation", payload.purpose, "aggregate", "completed",
                         {"study_ref": payload.study_ref, "count": len(records)})
        return {
            "study_ref": payload.study_ref, "count": len(records),
            "records": records,
            "note": "Synthetic scenarios are hypotheses, not empirical evidence.",
        }

    def status(self) -> Dict[str, Any]:
        return {
            "system": "IAM Human Behaviour Intelligence",
            "document": "26",
            "phase": 1,
            "status": "scientific_foundation_and_understanding_framework",
            "modules": 38,
            "technical_engines": 13,
            "advanced_capabilities": 8,
            "implemented_modules": sorted(modules.IMPLEMENTED),
            "implemented_capabilities": ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"],
            "validated_prediction_models": [
                mid for mid, record in self.predictor.validation.items() if record["validated"]
            ],
            "implemented_in_phase_1": [
                "E2 temporal intelligence", "E3 evidence verification", "E4 source reliability",
                "E5 language detection", "E6 cultural tagging", "E11 contradiction detection",
                "E12 knowledge gap detection", "E13 historical chronology", "A8 uncertainty intelligence",
            ],
            "prediction_emission": "withheld_until_validated",
            "local_first": True,
        }
