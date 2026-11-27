"""Document 26 (OD-45): Phase 1 HBI tests.

No network, no database, no model calls. Tests verify epistemic discipline,
governance gates and the A8 refusal to predict.
"""

import unittest

from app.services.hbi import GovernanceRefusal, HBIService
from app.services.hbi.schemas import (
    AnalogyEvaluationRequest,
    AnalogyRequest,
    AnalysisRequest,
    ChronologyInput,
    EvidenceItem,
    ForecastRequest,
    GraphEdgeRequest,
    GraphNodeRequest,
    KnowledgeRecordInput,
    ModuleAnalysisRequest,
    MultilingualIngestRequest,
    PredictionEvaluationRequest,
    PredictionRequest,
    ResearchDocumentInput,
    ResearchRequest,
    SourceRegisterRequest,
    TemporalRequest,
    TheoryComparisonRequest,
)
from app.services.hbi.prediction import accuracy, brier, ece, log_loss


class HBIPhase1Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    async def _store(self, claim="Community participation increased after the change", **overrides):
        payload = KnowledgeRecordInput(
            claim=claim,
            epistemic_type=overrides.pop("epistemic_type", "observation"),
            evidence=[
                EvidenceItem(
                    source_id="src_a", source_type="peer_reviewed_journal",
                    licence="cc-by", permitted_purpose="research",
                ),
                EvidenceItem(
                    source_id="src_b", source_type="national_archive",
                    licence="public_domain", permitted_purpose="research",
                ),
            ],
            confidence=0.8,
            module_ids=[12],
            context_dimensions={"behaviour": {"observed": True}},
            **overrides,
        )
        return await self.service.add_record(payload)

    async def test_status_declares_phase_and_counts(self):
        status = self.service.status()
        self.assertEqual(status["phase"], 1)
        self.assertEqual(status["modules"], 38)
        self.assertEqual(status["technical_engines"], 13)
        self.assertEqual(status["prediction_emission"], "withheld_until_validated")

    async def test_verified_claim_requires_independent_sources(self):
        record = await self._store()
        self.assertEqual(record["evidence_class"], "verified")
        self.assertEqual(record["epistemic_type"], "observation")

    async def test_unverified_claim_from_single_weak_source(self):
        payload = KnowledgeRecordInput(
            claim="Some people appear disinterested",
            epistemic_type="interpretation",
            alternatives=["They did not see the message"],
            evidence=[EvidenceItem(source_id="post_1", source_type="social_media")],
        )
        record = await self.service.add_record(payload)
        self.assertEqual(record["evidence_class"], "unverified")

    async def test_epistemic_discipline_enforced(self):
        with self.assertRaises(ValueError):
            await self.service.add_record(KnowledgeRecordInput(
                claim="X", epistemic_type="observation",
            ))
        with self.assertRaises(ValueError):
            await self.service.add_record(KnowledgeRecordInput(
                claim="X", epistemic_type="interpretation",
                evidence=[EvidenceItem(source_id="s", source_type="survey")],
            ))
        with self.assertRaises(ValueError):
            await self.service.add_record(KnowledgeRecordInput(
                claim="X", epistemic_type="hypothesis", alternatives=["Y"],
            ))

    async def test_scope_tier_consistency(self):
        with self.assertRaises(ValueError):
            await self.service.add_record(KnowledgeRecordInput(
                claim="X", epistemic_type="observation", scope="individual",
                evidence=[EvidenceItem(source_id="s", source_type="survey")],
            ))

    async def test_prohibited_purpose_blocked(self):
        with self.assertRaises(GovernanceRefusal) as ctx:
            await self.service.analyse(AnalysisRequest(
                question="How would they react?", purpose="manipulation",
            ))
        self.assertEqual(ctx.exception.code, "PURPOSE_MISMATCH")

    async def test_individual_scope_requires_consented_task(self):
        with self.assertRaises(GovernanceRefusal) as ctx:
            await self.service.research(ResearchRequest(query="profile them", purpose="general_research", scope="individual"))
        self.assertEqual(ctx.exception.code, "SCOPE_VIOLATION")

    async def test_a8_refusal_without_evidence(self):
        result = await self.service.analyse(AnalysisRequest(
            question="How will the community respond?", purpose="community_planning",
        ))
        self.assertIsNotNone(result["refusal"])
        self.assertEqual(result["refusal"]["code"], "INSUFFICIENT_EVIDENCE")

    async def test_prediction_withheld_and_logged(self):
        result = await self.service.predict(PredictionRequest(
            question="Will participation rise?", target="participation",
            purpose="community_planning", time_horizon="30 days",
        ))
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["probability"], {})
        self.assertIn(result["refusal"]["code"],
                      {"A8_MODEL_NOT_VALIDATED", "A8_UNRELIABLE_PREDICTION_CONTEXT"})
        self.assertEqual(self.service.core.audit_log[-1]["outcome"], "refused")

    async def test_contradictions_preserved(self):
        await self._store("Higher trust increases cooperation")
        await self._store("Higher trust reduces cooperation")
        result = await self.service.detect_contradictions()
        self.assertGreaterEqual(result["count"], 1)
        self.assertEqual(result["contradictions"][0]["resolution"], "unresolved")

    async def test_chronology_keeps_uncertainty_and_overlaps(self):
        result = self.service.resolve_chronology(ChronologyInput(
            events=[
                {"event_id": "e1", "name": "Event A", "date": {"value": "-0441", "precision": "year", "confidence": 0.7, "calendar": "Gregorian"}},
                {"event_id": "e2", "name": "Event B", "date": {"value": "1914-1918", "precision": "year", "confidence": 0.9}},
                {"event_id": "e3", "name": "Undated"},
            ],
            uncertain_periods=[{"label": "gap", "earliest": "-0500", "latest": "-0400"}],
            conflicting_accounts=[{"account_a": "A", "account_b": "B", "resolution_status": "unresolved"}],
        ))
        self.assertEqual(len(result["ordered_events"]), 3)
        self.assertTrue(result["ordered_events"][-1]["undated"])
        self.assertEqual(len(result["conflicting_accounts"]), 1)
        self.assertTrue(any(r["relation"] in {"before", "overlaps", "concurrent"} for r in result["relations"]))

    async def test_gap_detection_triggers_research(self):
        await self._store()
        result = await self.service.gaps("community response")
        self.assertIn("context_dimension::emotion", result["gaps"])
        self.assertTrue(result["research_triggers"])


class HBIEngineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    async def test_ingestion_accepts_licensed_research(self):
        result = await self.service.ingest(ResearchDocumentInput(
            source_id="study_1",
            title="Community trust study",
            text=("In this study, community trust increased after the programme. "
                  "People responded more cooperatively when information was clear."),
            source_type="peer_reviewed_journal",
            licence="cc-by",
            permitted_purpose="research",
            region="south_africa",
            module_ids=[1],
        ))
        self.assertEqual(result["language"], "en")
        self.assertIn("south_african_context", result["cultural_tags"])
        self.assertGreaterEqual(len(result["accepted"]), 1)
        self.assertEqual(result["quarantined"], [])

    async def test_ingestion_quarantines_unlicensed_material(self):
        result = await self.service.ingest(ResearchDocumentInput(
            source_id="blog_1", title="Post", text="People behave differently in groups every day here.",
            source_type="blog", permitted_purpose="research",
        ))
        self.assertIn("licence_missing", result["quarantined"])
        self.assertEqual(result["accepted"], [])
        self.assertEqual(self.service.quarantine()["count"], 1)

    async def test_module_framework_and_a8_for_unimplemented(self):
        await self._store()
        modules = self.service.list_modules()
        self.assertEqual(modules["count"], 38)
        result = await self.service.analyse_module(1, ModuleAnalysisRequest(
            question="community behaviour", purpose="community_planning",
        ))
        self.assertEqual(result["status"], "implemented")
        evaluation = await self.service.analyse_module(15, ModuleAnalysisRequest(
            question="evaluation", purpose="community_planning",
        ))
        self.assertEqual(evaluation["status"], "implemented")
        unknown = await self.service.analyse_module(99, ModuleAnalysisRequest(
            question="unknown", purpose="community_planning",
        ))
        self.assertEqual(unknown["error"], "UNKNOWN_MODULE")

    async def test_module_15_evaluation_surface(self):
        result = await self.service.analyse_module(15, ModuleAnalysisRequest(
            question="model performance", purpose="evaluation",
        ))
        self.assertEqual(result["module_id"], 15)
        self.assertTrue(result["models"])
        self.assertIn("not an authorisation", result["caveat"])

    async def test_module_governance_gate(self):
        with self.assertRaises(GovernanceRefusal):
            await self.service.analyse_module(1, ModuleAnalysisRequest(
                question="profile", purpose="sensitive_trait_inference",
            ))

    async def test_temporal_engine_detects_change(self):
        for year in ("2019", "2024"):
            await self.service.add_record(KnowledgeRecordInput(
                claim=f"Community participation observed in {year}",
                epistemic_type="observation",
                evidence=[EvidenceItem(source_id=year, source_type="survey", licence="cc-by")],
                context_dimensions={"time": {"value": year}},
            ))
        result = await self.service.temporal(TemporalRequest(question="participation", purpose="research"))
        self.assertEqual(len(result["buckets"]), 2)
        self.assertEqual(result["undated_records"], 0)

    async def test_db_backed_hydration(self):
        class Result:
            def __init__(self, rows):
                self.rows = rows
            def scalars(self):
                return self
            def all(self):
                return self.rows

        class FakeDB:
            def __init__(self):
                self.rows = []
            def add(self, obj):
                self.rows.append(obj)
            async def flush(self):
                return None
            async def execute(self, statement):
                from app.models.hbi import HBIKnowledgeRecord
                return Result([r for r in self.rows if isinstance(r, HBIKnowledgeRecord)])

        db = FakeDB()
        writer = HBIService(db)
        await writer.add_record(KnowledgeRecordInput(
            claim="Verified historical pattern", epistemic_type="observation",
            evidence=[EvidenceItem(source_id="a", source_type="national_archive", licence="public_domain")],
        ))
        reader = HBIService(db)
        records = await reader.ensure_loaded()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["claim"], "Verified historical pattern")

    async def _store(self, claim="Community participation increased after the change"):
        return await self.service.add_record(KnowledgeRecordInput(
            claim=claim,
            epistemic_type="observation",
            evidence=[
                EvidenceItem(source_id="a", source_type="peer_reviewed_journal", licence="cc-by", permitted_purpose="research"),
                EvidenceItem(source_id="b", source_type="national_archive", licence="public_domain", permitted_purpose="research"),
            ],
            confidence=0.8,
            module_ids=[1],
            context_dimensions={"behaviour": {"observed": True}},
        ))


class HBIPredictionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    def test_scoring_rules(self):
        pairs = [(0.8, 1), (0.2, 0)]
        self.assertEqual(brier(pairs), 0.04)
        self.assertEqual(ece(pairs), 0.2)
        self.assertEqual(accuracy(pairs), 1.0)
        self.assertLess(log_loss(pairs), 0.5)

    def test_backtest_excludes_post_cutoff_outcomes(self):
        from app.services.hbi.prediction import HistoricalCase, backtest
        cases = [
            HistoricalCase("leaked", cutoff_year=2020, outcome_year=2021, features={"support": 1.0}, outcome=1),
            HistoricalCase("valid", cutoff_year=2030, outcome_year=2021, features={"support": 1.0}, outcome=1),
            HistoricalCase("valid2", cutoff_year=2030, outcome_year=2022, features={"against_support": 1.0}, outcome=0),
        ]
        result = backtest(cases)
        self.assertIn("leaked", result["excluded_cases"])
        self.assertGreaterEqual(result["scores"]["n"], 1)

    async def test_prediction_withheld_until_validated(self):
        request = PredictionRequest(
            question="Will participation rise?", target="participation",
            purpose="community_planning", features={"support": 2.0},
        )
        refused = await self.service.predict(request)
        self.assertIn(refused["refusal"]["code"],
                      {"A8_MODEL_NOT_VALIDATED", "A8_UNRELIABLE_PREDICTION_CONTEXT"})

        from app.services.hbi.prediction import HistoricalCase
        cases = []
        for index in range(8):
            outcome = index % 2
            cases.append(HistoricalCase(
                case_id=f"case_{index}", cutoff_year=2030,
                outcome_year=2031 if index >= 6 else 2020 + index,
                features={"support": 2.0} if outcome else {"against_support": 2.0},
                outcome=outcome,
            ))
        validation = self.service.validate_model("baseline", cases)
        self.assertTrue(validation["validated"], validation)
        for claim in ("Trust increased in the community", "Information was shared widely"):
            await self.service.add_record(KnowledgeRecordInput(
                claim=claim,
                epistemic_type="observation",
                evidence=[EvidenceItem(source_id="a", source_type="peer_reviewed_journal",
                                       licence="cc-by", permitted_purpose="research")],
                module_ids=[1, 10],
                context_dimensions={
                    "behaviour": {"observed": True}, "environment": {"region": "test"},
                    "emotion": {"expressed": "neutral"}, "motivation": {"stated": "none"},
                    "cognition": {"belief": "unknown"}, "social_influence": {"norm": "unknown"},
                    "outcome": {"recorded": True},
                },
            ))
        emitted = await self.service.predict(request)
        self.assertIn("positive", emitted["probability"])
        self.assertNotEqual(emitted["confidence"], emitted["probability"]["positive"])
        self.assertEqual(emitted["causal_status"], "correlational")

    async def test_division_two_modules(self):
        await self.service.add_record(KnowledgeRecordInput(
            claim="Clear incentives increased participation across the community",
            epistemic_type="observation",
            evidence=[EvidenceItem(source_id="a", source_type="survey", licence="cc-by")],
            module_ids=[5, 29],
        ))
        result = await self.service.analyse_module(5, ModuleAnalysisRequest(
            question="incentives and participation", purpose="community_planning",
        ))
        self.assertEqual(result["status"], "implemented")
        self.assertGreaterEqual(len(result["epistemic_objects"]), 1)

    async def test_authorised_source_registry(self):
        from app.services.hbi.sources import AuthorisedSource, SourceNotAuthorised
        self.service.register_source(SourceRegisterRequest(
            source_id="src", domain="example.org", source_type="news", licence="cc-by",
        ))
        def fake_fetch(url):
            return {"robots_allowed": True, "text": "Community behaviour text", "title": "Example"}
        fetched = self.service.fetch_source("https://example.org/page", fake_fetch)
        self.assertEqual(fetched["source_id"], "src")
        with self.assertRaises(SourceNotAuthorised):
            self.service.fetch_source("https://unlisted.example/page", fake_fetch)
        self.service.sources.register(AuthorisedSource(
            source_id="robots", domain="robots.example", source_type="news", licence="cc-by",
        ))
        with self.assertRaises(SourceNotAuthorised):
            self.service.fetch_source("https://robots.example/page", lambda url: {"robots_allowed": False})


class HBIAdvancedTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    async def test_division_three_four_modules_registered(self):
        implemented = self.service.list_modules()["implemented"]
        for module_id in (8, 10, 12, 26, 28, 31, 33, 36, 38):
            self.assertIn(module_id, implemented)

    async def test_a1_self_directed_research(self):
        result = await self.service.self_directed_research("community response", "research")
        self.assertGreater(result["count"], 0)
        self.assertTrue(all(t["status"] == "candidate" for t in result["triggers"]))
        with self.assertRaises(GovernanceRefusal):
            await self.service.self_directed_research("profile", "manipulation")

    async def test_a2_theory_comparison(self):
        request = TheoryComparisonRequest(
            theories=[
                {"id": "t1", "name": "Theory one", "predictions": {"c1": 0.9, "c2": 0.1}},
                {"id": "t2", "name": "Theory two", "predictions": {"c1": 0.2, "c2": 0.8}},
            ],
            cases=[{"case_id": "c1", "outcome": 1}, {"case_id": "c2", "outcome": 0}],
        )
        result = self.service.compare_theories(request)
        self.assertEqual(result["current_best_supported"], "t1")
        self.assertIn("t2", result["still_viable"])

    async def test_a3_hypothesis_generation_stores_falsifiers(self):
        await self._store()
        result = await self.service.generate_hypotheses("research")
        self.assertGreater(result["count"], 0)
        self.assertTrue(all(h["falsifier"] for h in result["hypotheses"]))
        stored = await self.service.search_records(epistemic_type="hypothesis")
        self.assertEqual(stored["count"], result["count"])

    async def test_a4_analogy_can_reject_comparison(self):
        strong = self.service.analogy(AnalogyRequest(
            current={"similarities": {k: 1.0 for k in ("contextual", "economic", "political", "social", "behavioural", "technological")}, "differences": []},
            precedent={"event_id": "crisis_a", "evidence_class": "verified"},
        ))
        self.assertEqual(strong["verdict"], "applicable")
        weak = self.service.analogy(AnalogyRequest(
            current={"similarities": {}, "differences": ["institutions", "technology", "demographics"]},
            precedent={"event_id": "crisis_b", "evidence_class": "unverified"},
        ))
        self.assertEqual(weak["verdict"], "weak_or_misleading")

    async def test_a5_prediction_self_evaluation(self):
        refused = self.service.evaluate_prediction(PredictionEvaluationRequest(
            prediction={"refusal": {"code": "A8_MODEL_NOT_VALIDATED", "what_would_change": ["validation"]}},
            outcome=1,
        ))
        self.assertEqual(refused["error_type"], "withheld_prediction")
        failed = self.service.evaluate_prediction(PredictionEvaluationRequest(
            prediction={"probability": {"positive": 0.95}, "uncertainty": {"evidence_gap": "high"}},
            outcome=0,
        ))
        self.assertIn("evidence_gap", failed["error_type"])

    async def test_historical_graph_and_timeline_ingest(self):
        first = await self.service.add_graph_node(GraphNodeRequest(
            node_ref="evt_a", node_type="historical_event", label="Crisis A",
            date_value={"value": "1929"}, evidence_class="verified",
        ))
        second = await self.service.add_graph_node(GraphNodeRequest(
            node_ref="evt_b", node_type="historical_event", label="Response B",
            date_value={"value": "1933"},
        ))
        await self.service.add_graph_edge(GraphEdgeRequest(
            from_ref=first["node_ref"], to_ref=second["node_ref"],
            relation="preceded", confidence=0.8,
        ))
        expanded = self.service.expand_graph("evt_a", 1)
        self.assertEqual(len(expanded["nodes"]), 2)
        self.assertEqual(self.service.query_graph(relation="preceded")["count"], 1)

        ingest = await self.service.ingest_timeline(ChronologyInput(
            events=[
                {"event_id": "e1", "name": "Event one", "date": {"value": "1000", "precision": "year", "confidence": 0.8}},
                {"event_id": "e2", "name": "Event two", "date": {"value": "1200", "precision": "year", "confidence": 0.7}},
            ],
            conflicting_accounts=[{"account_a": "A", "account_b": "B", "resolution_status": "unresolved"}],
        ))
        self.assertEqual(ingest["nodes_added"], 2)
        self.assertEqual(ingest["conflicting_accounts"], 1)

    async def _store(self):
        return await self.service.add_record(KnowledgeRecordInput(
            claim="Community trust increased after the programme",
            epistemic_type="observation",
            evidence=[EvidenceItem(source_id="a", source_type="peer_reviewed_journal", licence="cc-by", permitted_purpose="research")],
            module_ids=[1],
        ))


class HBIAdvancedCapabilitiesTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    async def test_a6_cross_disciplinary_fusion(self):
        from app.services.hbi.schemas import CrossDisciplinaryRequest
        request = CrossDisciplinaryRequest(
            question="How will the community respond?",
            claims_by_discipline={
                "psychology": [{"claim": "Trust increased", "confidence": 0.8, "evidence_class": "verified"}],
                "history": [{"claim": "Trust decreased", "confidence": 0.6, "evidence_class": "well_supported"}],
            },
            calibration_weights={"psychology": 0.5, "history": 0.5},
        )
        result = self.service.cross_disciplinary(request)
        self.assertEqual(result["status"], "cross_disciplinary_interpretation")
        self.assertEqual(result["single_discipline_dominance"], [])
        self.assertGreaterEqual(result["contradictions"]["count"], 1)

    async def test_a7_revision_preserves_lineage(self):
        from app.services.hbi.schemas import RevisionRequest
        original = await self._store()
        revision = await self.service.revise(RevisionRequest(
            old_ref=original["record_ref"],
            rationale="stronger independent source",
            payload=KnowledgeRecordInput(
                claim="Community participation increased after the revised programme",
                epistemic_type="observation",
                evidence=[EvidenceItem(source_id="b", source_type="national_archive", licence="public_domain", permitted_purpose="research")],
            ),
        ))
        self.assertEqual(revision["version"], 2)
        lineage = self.service.lineage(revision["new_ref"])
        self.assertEqual(lineage["length"], 2)
        self.assertEqual(self.service.store.get(original["record_ref"])["status"], "superseded")

    async def test_a8_refuses_when_no_evidence(self):
        result = self.service.uncertainty_assessment("anything", "research")
        self.assertEqual(result["verdict"], "unreliable")
        self.assertEqual(result["refusal"]["code"], "A8_UNRELIABLE_PREDICTION_CONTEXT")
        with self.assertRaises(GovernanceRefusal):
            self.service.uncertainty_assessment("anything", "manipulation")

    async def test_manipulation_detection_is_defensive(self):
        from app.services.hbi.schemas import ManipulationRequest
        result = self.service.analyse_manipulation(ManipulationRequest(
            texts=["Act now, everyone knows this is urgent."],
        ))
        patterns = {item["pattern"] for item in result["indicators"]}
        self.assertIn("urgency_pressure", patterns)
        self.assertIn("certainty_pressure", patterns)
        self.assertTrue(result["defensive_use_only"])
        self.assertIn("not diagnoses", result["caveat"])

    async def test_bayesian_and_ensemble_models(self):
        from app.services.hbi.prediction import BetaBinomialModel, EnsembleForecaster, HistoricalCase
        cases = [
            HistoricalCase(f"c{i}", 2030, 2020 + i, {"support": 1.0} if i % 2 else {"against_support": 1.0}, i % 2)
            for i in range(6)
        ]
        bayesian = BetaBinomialModel()
        bayesian.fit(cases)
        probability = bayesian.predict({"support": 1.0})
        self.assertTrue(0.0 <= probability <= 1.0)
        interval = bayesian.interval()
        self.assertLessEqual(interval["lower"], interval["upper"])
        ensemble = EnsembleForecaster()
        ensemble.fit(cases)
        self.assertTrue(0.0 <= ensemble.predict({"support": 1.0}) <= 1.0)
        self.assertIn("beta_binomial", self.service.predictor.models)
        self.assertIn("ensemble", self.service.predictor.models)

    async def test_validated_model_still_refused_without_context(self):
        from app.services.hbi.prediction import HistoricalCase
        cases = []
        for index in range(8):
            outcome = index % 2
            cases.append(HistoricalCase(
                case_id=f"c{index}", cutoff_year=2030,
                outcome_year=2031 if index >= 6 else 2020 + index,
                features={"support": 2.0} if outcome else {"against_support": 2.0},
                outcome=outcome,
            ))
        self.assertTrue(self.service.validate_model("baseline", cases)["validated"])
        result = await self.service.predict(PredictionRequest(
            question="Will it happen?", target="event", purpose="research",
            features={"support": 1.0},
        ))
        self.assertEqual(result["refusal"]["code"], "A8_UNRELIABLE_PREDICTION_CONTEXT")

    async def _store(self):
        return await self.service.add_record(KnowledgeRecordInput(
            claim="Community participation increased after the programme",
            epistemic_type="observation",
            evidence=[EvidenceItem(source_id="a", source_type="peer_reviewed_journal", licence="cc-by", permitted_purpose="research")],
        ))


class HBIForecastHistoricalTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    async def test_module_thirteen_registered_and_gated(self):
        self.assertIn(13, self.service.list_modules()["implemented"])
        result = await self.service.forecast(ForecastRequest(
            question="What happens next?", target="participation", purpose="research",
            features={"support": 1.0},
        ))
        self.assertIsNone(result["prediction_id"])
        self.assertIn("refusal", result)

    async def test_forecast_emits_after_validation(self):
        from app.services.hbi.prediction import HistoricalCase
        cases = []
        for index in range(8):
            outcome = index % 2
            cases.append(HistoricalCase(
                case_id=f"c{index}", cutoff_year=2030,
                outcome_year=2031 if index >= 6 else 2020 + index,
                features={"support": 2.0} if outcome else {"against_support": 2.0},
                outcome=outcome,
            ))
        self.assertTrue(self.service.validate_model("logistic", cases)["validated"])
        for claim in ("Trust increased in the community", "Information was shared widely"):
            await self.service.add_record(KnowledgeRecordInput(
                claim=claim, epistemic_type="observation", module_ids=[1, 10],
                evidence=[EvidenceItem(source_id="a", source_type="peer_reviewed_journal",
                                       licence="cc-by", permitted_purpose="research")],
                context_dimensions={
                    "behaviour": {"observed": True}, "environment": {"region": "test"},
                    "emotion": {"expressed": "neutral"}, "motivation": {"stated": "none"},
                    "cognition": {"belief": "unknown"}, "social_influence": {"norm": "unknown"},
                    "outcome": {"recorded": True},
                },
            ))
        result = await self.service.forecast(ForecastRequest(
            question="What happens next?", target="participation", purpose="research",
            model_id="logistic", features={"support": 1.0},
        ))
        self.assertIsNotNone(result["prediction_id"])
        self.assertTrue(result["normalised"])

    async def test_historical_modules_implemented(self):
        implemented = self.service.list_modules()["implemented"]
        for module_id in range(16, 24):
            self.assertIn(module_id, implemented)
        result = await self.service.historical_module(22, "recurring patterns across periods")
        self.assertEqual(result["status"], "implemented")
        result_23 = await self.service.historical_module(23, "comparable crisis in 1929")
        self.assertEqual(result_23["status"], "implemented")

    async def test_causal_discipline(self):
        result = self.service.causal("Does trust cause cooperation?")
        self.assertEqual(result["causal_status"], "correlational")
        self.assertIn("refusal", result)
        from app.services.hbi.schemas import CausalStatus
        await self.service.add_record(KnowledgeRecordInput(
            claim="Verified causal effect", epistemic_type="observation",
            evidence=[EvidenceItem(source_id="a", source_type="peer_reviewed_journal", licence="cc-by")],
            causal_status=CausalStatus.CAUSAL,
        ))
        verified = self.service.causal("Does trust cause cooperation?")
        self.assertEqual(verified["causal_status"], "causal")
        self.assertIn("parallel_trends", verified["assumptions_required"])

    async def test_difference_in_differences(self):
        from app.services.hbi.causal import difference_in_differences
        result = difference_in_differences(10, 18, 10, 12)
        self.assertEqual(result["estimate"], 6)
        self.assertEqual(result["identification"], "conditional")

    async def test_analogy_evaluation_measures_lift(self):
        request = AnalogyEvaluationRequest(
            current={"similarities": {k: 1.0 for k in ("contextual", "economic", "political", "social", "behavioural", "technological")}},
            precedents=[
                {"case_id": "c1", "event_id": "e1", "evidence_class": "verified"},
                {"case_id": "c2", "event_id": "e2", "evidence_class": "verified"},
            ],
            cases=[{"case_id": "c1", "outcome": 1}, {"case_id": "c2", "outcome": 0}],
        )
        result = self.service.evaluate_analogies(request)
        self.assertEqual(len(result["evaluated"]), 2)
        self.assertIn("lift", result)


class HBICompletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    async def test_module_27_multi_factor(self):
        self.assertIn(27, self.service.list_modules()["implemented"])
        result = await self.service.civilisation("Why did the civilisation decline?")
        self.assertEqual(result["module_id"], 27)
        self.assertFalse(result["single_cause_claim"])
        self.assertIn("institutional_trust", result["factors"])

    async def test_multilingual_ingestion_and_duplicates(self):
        from app.services.hbi.schemas import ResearchDocumentInput
        documents = [
            ResearchDocumentInput(
                source_id="d1", title="Study A",
                text="Community trust increased after the programme and people cooperated.",
                source_type="peer_reviewed_journal", licence="cc-by", permitted_purpose="research",
            ),
            ResearchDocumentInput(
                source_id="d2", title="Study A copy",
                text="Community trust increased after the programme and people cooperated.",
                source_type="peer_reviewed_journal", licence="cc-by", permitted_purpose="research",
            ),
        ]
        result = await self.service.ingest_multilingual(MultilingualIngestRequest(documents=documents))
        self.assertEqual(result["documents"], 2)
        self.assertEqual(len(result["duplicates"]), 1)
        self.assertEqual(result["results"][1]["status"], "skipped_duplicate")
        self.assertIn("language_detail", result["results"][0])
        self.assertEqual(result["results"][0]["translation"]["status"], "translation_not_performed")

    async def test_language_script_detection(self):
        from app.services.hbi.ingestion import detect_language_detail
        detail = detect_language_detail("الناس في المجتمع يبحثون عن الثقة")
        self.assertEqual(detail["script"], "arabic")
        self.assertLessEqual(detail["confidence"], 0.95)

    async def test_acceptance_gates_pass(self):
        await self.service.add_record(KnowledgeRecordInput(
            claim="Community trust increased after the programme",
            epistemic_type="observation",
            evidence=[EvidenceItem(source_id="a", source_type="peer_reviewed_journal",
                                   licence="cc-by", permitted_purpose="research")],
        ))
        await self.service.analyse(AnalysisRequest(question="trust", purpose="research"))
        result = await self.service.run_acceptance()
        self.assertTrue(result["passed"], result["failed"])
        self.assertGreaterEqual(result["count"], 10)


class HBIEvidenceValidationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    async def test_licensed_corpus_ingestion(self):
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text(
                "Community trust increased after the programme and people cooperated.",
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            def entry(source_id: str, purposes: list) -> dict:
                return {
                    "source_id": source_id, "path": "a.txt",
                    "source": {"title": "Study A", "origin": "https://example.org",
                               "collection_date": "2026-11-27"},
                    "licensing": {
                        "licence_id": "CC-BY-4.0",
                        "licence_url": "https://creativecommons.org/licenses/by/4.0/",
                        "commercial_use_allowed": True, "attribution_required": True,
                        "ingestion_allowed": True, "storage_allowed": True,
                        "analysis_allowed": True, "model_training_allowed": False,
                    },
                    "permitted_purposes": purposes,
                    "lawful_basis": {"applies_to_living_persons": False, "basis": "not_applicable"},
                    "privacy": {"contains_personal_information": False},
                    "governance": {"validation_status": "pending"},
                }

            manifest.write_text(json.dumps([
                entry("licensed_1", ["research", "historical", "aggregate_analysis"]),
                entry("bad_1", ["manipulation"]),
            ]), encoding="utf-8")
            from app.services.hbi.schemas import CorpusIngestRequest
            result = await self.service.ingest_corpus(
                CorpusIngestRequest(manifest_path=str(manifest), root=str(root))
            )
            self.assertEqual(result["documents"], 2)
            self.assertGreaterEqual(result["records_accepted"], 1)
            statuses = [item.get("status") for item in result["results"]]
            self.assertIn("rejected", statuses)
            self.assertEqual(result["corpus_state"], "validated")

    async def test_empirical_source_calibration(self):
        from app.services.hbi.schemas import SourceCalibrationRequest
        from app.services.hbi.evidence import rate_source
        cases = [
            {"source_type": "survey", "outcome": 1},
            {"source_type": "survey", "outcome": 1},
            {"source_type": "survey", "outcome": 1},
            {"source_type": "news", "outcome": 0},
        ]
        result = self.service.calibrate_sources(SourceCalibrationRequest(cases=cases))
        self.assertIn("survey", result["empirical_sources"])
        rating = rate_source("survey", "cc-by", "research",
                             learned_weights=self.service.ingestion.learned_weights)
        self.assertIn("empirically_calibrated", rating["limitations"][0])

    async def test_module_14_framework_integration(self):
        result = await self.service.analyse_module(14, ModuleAnalysisRequest(
            question="Act now, everyone knows this is urgent.",
            purpose="defensive_analysis",
        ))
        self.assertEqual(result["status"], "implemented")
        self.assertTrue(result["defensive_use_only"])
        self.assertGreater(result["count"], 0)

    async def test_backtest_library_provenance(self):
        summary = self.service.backtest_library()
        self.assertEqual(summary["count"], 12)
        self.assertTrue(summary["leakage_precondition"])
        self.assertIn("illustrative", summary["status"])
        validation = self.service.validate_on_library("ensemble")
        self.assertIn("scores", validation)


class HBIGovernanceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    async def test_dual_use_prohibits_offensive_capabilities(self):
        from app.services.hbi.schemas import DualUseRequest
        result = self.service.dual_use_review(DualUseRequest(
            capability="targeted_influence", markers=["influence_content", "targeting"],
            purpose="campaign",
        ))
        self.assertEqual(result["decision"], "PROHIBITED")
        self.assertIn("do_not_deploy", result["required_controls"])

    async def test_dual_use_restricts_manipulation_detection(self):
        from app.services.hbi.schemas import DualUseRequest
        result = self.service.dual_use_review(DualUseRequest(
            capability="module_14", markers=["manipulation_detection"],
            purpose="defensive_analysis",
        ))
        self.assertEqual(result["decision"], "RESTRICTED")
        self.assertIn("defensive_use_only", result["required_controls"])

    async def test_dpia_is_technical_input_only(self):
        result = self.service.dpia()
        self.assertIn("POPIA", str(result["legal_frameworks"]))
        self.assertIn("GDPR", str(result["legal_frameworks"]))
        self.assertEqual(len(result["data_categories"]), 4)
        self.assertIn("not a clearance", result["note"])

    async def test_human_oversight_for_consequential_decisions(self):
        from app.services.hbi.schemas import OversightRequest
        result = self.service.oversight(OversightRequest(
            decision_type="employment",
            evidence={"probability": {"positive": 0.8}, "confidence": 0.6,
                      "alternatives": ["no evidence"], "uncertainty": {"evidence_gap": "high"}},
        ))
        self.assertFalse(result["automated_decision_permitted"])
        self.assertTrue(result["human_review_required"])
        self.assertTrue(result["evidence_packet"]["disconfirming_evidence_required"])
        ordinary = self.service.oversight(OversightRequest(decision_type="research_summary"))
        self.assertEqual(ordinary["status"], "analysis_only")


class HBIDeploymentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService(local_signoff_file=False)

    async def _prepare(self):
        await self.service.add_record(KnowledgeRecordInput(
            claim="Community trust increased after the programme",
            epistemic_type="observation",
            evidence=[EvidenceItem(source_id="a", source_type="peer_reviewed_journal",
                                   licence="cc-by", permitted_purpose="research")],
        ))
        await self.service.analyse(AnalysisRequest(question="trust", purpose="research"))

    async def test_readiness_requires_signoff(self):
        from app.services.hbi.schemas import DPIASignoffRequest
        await self._prepare()
        before = await self.service.deployment_readiness()
        self.assertFalse(before["ready"])
        self.assertIn("dpia_signoff_required", before["blockers"])
        await self.service.sign_off_dpia(DPIASignoffRequest(
            reviewer="authorised-reviewer", decision="approved",
            basis="risks mitigated; residual risk accepted",
        ))
        after = await self.service.deployment_readiness()
        self.assertTrue(after["ready"], after["blockers"])

    async def test_prohibited_capability_blocks_deployment(self):
        from app.services.hbi.schemas import DPIASignoffRequest, DualUseRequest
        await self._prepare()
        await self.service.sign_off_dpia(DPIASignoffRequest(
            reviewer="authorised-reviewer", decision="approved", basis="reviewed",
        ))
        self.service.dual_use_review(DualUseRequest(
            capability="targeting", markers=["targeting"], purpose="campaign",
        ))
        result = await self.service.deployment_readiness()
        self.assertFalse(result["ready"])
        self.assertTrue(any(b.startswith("prohibited_capability") for b in result["blockers"]))

    async def test_deployment_config_blockers(self):
        from app.services.hbi.schemas import DPIASignoffRequest
        await self._prepare()
        await self.service.sign_off_dpia(DPIASignoffRequest(
            reviewer="authorised-reviewer", decision="approved", basis="reviewed",
        ))
        result = await self.service.deployment_readiness({"rollback_tested": False})
        self.assertIn("rollback_not_tested", result["blockers"])

    async def test_signoff_is_durable(self):
        from app.services.hbi.schemas import DPIASignoffRequest

        class Result:
            def __init__(self, rows):
                self.rows = rows
            def scalars(self):
                return self
            def all(self):
                return self.rows

        class FakeDB:
            def __init__(self):
                self.rows = []
            def add(self, obj):
                self.rows.append(obj)
            async def flush(self):
                return None
            async def execute(self, statement):
                from app.models.hbi import HBIDPIASignoff
                return Result([r for r in self.rows if isinstance(r, HBIDPIASignoff)])

        db = FakeDB()
        writer = HBIService(db)
        await writer.sign_off_dpia(DPIASignoffRequest(
            reviewer="reviewer-a", decision="approved", basis="reviewed",
        ))
        reader = HBIService(db)
        signoffs = await reader.load_dpia_signoffs()
        self.assertEqual(len(signoffs), 1)
        self.assertEqual(signoffs[0]["reviewer"], "reviewer-a")

    async def test_signoff_validation(self):
        from app.services.hbi.schemas import DPIASignoffRequest
        with self.assertRaises(ValueError):
            await self.service.sign_off_dpia(DPIASignoffRequest(
                reviewer="", decision="approved", basis="x",
            ))


class HBIValidationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    async def _add_case(self, index: int, population: str, confidence: float,
                        verified: bool = True, with_outcome: bool = True,
                        provenance_kind: str = "direct_observation"):
        from app.services.hbi.schemas import EvidenceClass
        source_type = "peer_reviewed_journal" if verified else "social_media"
        dims = {
            "time": {"value": str(2000 + index)},
            "outcome": {"observed_at": str(2010 + index), "value": 1},
        } if with_outcome else {"time": {"value": str(2000 + index)}}
        return await self.service.add_record(KnowledgeRecordInput(
            claim=f"Recorded community outcome {index}",
            epistemic_type="observation",
            evidence_class=EvidenceClass.VERIFIED if verified else EvidenceClass.UNVERIFIED,
            provenance_kind=provenance_kind,
            population=population,
            confidence=confidence,
            evidence=[EvidenceItem(source_id=f"s{index}", source_type=source_type,
                                   licence="cc-by", permitted_purpose="research")],
            context_dimensions=dims,
        ))

    async def test_cases_derived_only_from_verified_dated_records(self):
        await self._add_case(1, "group_a", 0.8)
        await self._add_case(2, "group_a", 0.2, verified=False)
        await self._add_case(3, "group_a", 0.6, with_outcome=False)
        result = self.service.validation_cases()
        self.assertEqual(result["case_count"], 1)
        self.assertEqual(result["provenance"], "derived_from_graded_records")
        self.assertEqual(len(result["excluded"]), 2)

    async def test_report_refuses_validation_without_real_cases(self):
        result = self.service.validation_report()
        self.assertEqual(result["verdict"], "not_validated")
        self.assertIn("insufficient_real_backtest_cases", result["blockers"])
        self.assertNotIn("illustrative", str(result["provenance"]))

    async def test_bias_disparity_detected(self):
        for index in range(5):
            await self._add_case(index, "group_a", 0.9)
            await self._add_case(index + 10, "group_b", 0.2)
        result = self.service.validation_bias()
        self.assertTrue(result["flag"])
        self.assertGreater(result["disparity"], result["disparity_threshold"])

    async def test_illustrative_fixtures_never_satisfy_validation(self):
        for index in range(10):
            await self._add_case(index, "fixture", 0.8,
                                 provenance_kind="illustrative_fixture")
        cases = self.service.validation_cases()
        self.assertEqual(cases["case_count"], 0)
        self.assertTrue(any(item["reason"] == "illustrative_fixture_excluded"
                            for item in cases["excluded"]))
        readiness = self.service.corpus_readiness()
        self.assertFalse(readiness["ready_for_validation"])
        self.assertEqual(readiness["illustrative_fixtures"], 10)

    async def test_licensed_corpus_counts_toward_readiness(self):
        from app.services.hbi.schemas import ResearchDocumentInput
        for index in range(10):
            await self.service.ingest(ResearchDocumentInput(
                source_id=f"licensed_{index}",
                title=f"Study {index}",
                text="Community trust increased after the programme in this observed group.",
                source_type="peer_reviewed_journal", licence="cc-by",
                permitted_purpose="research",
            ))
        readiness = self.service.corpus_readiness()
        self.assertGreaterEqual(readiness["licensed_records"], 10)
        self.assertTrue(readiness["ready_for_validation"])

    async def test_report_uses_derived_cases_at_scale(self):
        for index in range(10):
            await self._add_case(index, "cohort", 0.6 if index % 2 else 0.8)
        result = self.service.validation_report("evidence")
        self.assertNotIn("insufficient_real_backtest_cases", result["blockers"])
        self.assertIn("scores", result)


class HBICorpusGateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    def _manifest(self, **overrides):
        from app.services.hbi.schemas import CorpusSourceManifest
        payload = {
            "source_id": "SRC-GATE",
            "source": {"title": "Study", "origin": "https://example.org",
                       "collection_date": "2026-11-27"},
            "licensing": {
                "licence_id": "CC-BY-4.0",
                "licence_url": "https://creativecommons.org/licenses/by/4.0/",
                "ingestion_allowed": True, "storage_allowed": True, "analysis_allowed": True,
                "model_training_allowed": False,
            },
            "permitted_purposes": ["research", "historical", "aggregate_analysis"],
        }
        payload.update(overrides)
        return CorpusSourceManifest(**payload)

    async def test_missing_licence_is_rejected(self):
        from app.services.hbi.schemas import CorpusReviewRequest
        result = self.service.review_corpus_source(CorpusReviewRequest(
            manifest=self._manifest(licensing={}), intended_purpose="research",
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("licence_not_identified", result["rejected_reasons"])

    async def test_purpose_is_fail_closed(self):
        from app.services.hbi.schemas import CorpusReviewRequest
        result = self.service.review_corpus_source(CorpusReviewRequest(
            manifest=self._manifest(), intended_purpose="manipulation",
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("prohibited_purpose", result["rejected_reasons"])

    async def test_sensitive_processing_is_rejected(self):
        from app.services.hbi.schemas import CorpusReviewRequest
        manifest = self._manifest(privacy={"sensitive_trait_inference": True})
        result = self.service.review_corpus_source(CorpusReviewRequest(manifest=manifest))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("sensitive_processing_prohibited", result["rejected_reasons"])

    async def test_training_needs_separate_permission(self):
        from app.services.hbi.schemas import CorpusReviewRequest
        result = self.service.review_corpus_source(CorpusReviewRequest(
            manifest=self._manifest(), model_training=True,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("research_permission_does_not_authorise_model_training", result["rejected_reasons"])

    async def test_approval_audit_and_restriction(self):
        from app.services.hbi.schemas import CorpusRestrictionRequest, CorpusReviewRequest
        approved = self.service.review_corpus_source(CorpusReviewRequest(
            manifest=self._manifest(), approved_by="reviewer-1",
        ))
        self.assertEqual(approved["decision"], "approved")
        self.assertEqual(approved["approved_by"], "reviewer-1")
        self.assertEqual(self.service.corpus_state()["state"], "validated")
        audit = self.service.corpus_audit()
        self.assertEqual(audit["count"], 1)
        self.assertIn("licence_verification", audit["events"][0]["rules_applied"])
        self.service.restrict_corpus_source(CorpusRestrictionRequest(
            source_id="SRC-GATE", reason="permission revoked",
        ))
        self.assertEqual(self.service.corpus_state()["state"], "restricted")
        self.assertNotIn("SRC-GATE", self.service.corpus_governance.approved_ids())

    async def test_lawful_basis_is_separate_from_licence(self):
        from app.services.hbi.schemas import CorpusReviewRequest
        manifest = self._manifest(
            privacy={"contains_personal_information": True},
            lawful_basis={"applies_to_living_persons": True, "basis": "not_applicable"},
        )
        result = self.service.review_corpus_source(CorpusReviewRequest(manifest=manifest))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("lawful_basis_missing", result["rejected_reasons"])


class HBILifecycleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    async def test_drift_detected(self):
        from app.services.hbi.schemas import EvidenceClass
        for year, confidence in (("2010", 0.9), ("2011", 0.9), ("2012", 0.9),
                                 ("2020", 0.4), ("2021", 0.4), ("2022", 0.4)):
            await self.service.add_record(KnowledgeRecordInput(
                claim="Observed behaviour in period",
                epistemic_type="observation", evidence_class=EvidenceClass.VERIFIED,
                confidence=confidence,
                evidence=[EvidenceItem(source_id=year, source_type="peer_reviewed_journal",
                                       licence="cc-by")],
                context_dimensions={"time": {"value": year}},
            ))
        result = self.service.drift_report()
        self.assertTrue(result["drift_detected"])
        self.assertLess(result["confidence_delta"], -0.2)

    async def test_re_evaluation_plan_lists_unvalidated_models(self):
        result = self.service.re_evaluation_plan()
        self.assertGreater(result["count"], 0)
        self.assertTrue(any(task["model_id"] == "ensemble" for task in result["tasks"]))

    async def test_rollback_drill_passes(self):
        result = self.service.rollback_drill("ensemble")
        self.assertTrue(result["passed"])
        self.assertEqual(result["after_version"], result["before_version"])


class HBIPermissionEngineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    def _manifest(self, training: bool = True):
        from app.services.hbi.schemas import CorpusSourceManifest
        return CorpusSourceManifest(
            source_id="SRC-PERM",
            rights_holder="Research Institute",
            acquisition_method="partnership",
            source={"title": "Study", "origin": "https://example.org",
                    "collection_date": "2026-11-27"},
            licensing={
                "licence_id": "CC-BY-4.0",
                "licence_url": "https://creativecommons.org/licenses/by/4.0/",
                "permission_evidence": "agreement-1",
                "ingestion_allowed": True, "storage_allowed": True,
                "analysis_allowed": True, "derivative_allowed": True,
                "model_training_allowed": training,
            },
            permitted_purposes=["research", "historical", "aggregate_analysis"],
        )

    async def test_legal_context_is_unverified_until_counsel(self):
        result = self.service.legal_context()
        self.assertTrue(all(item["status"] == "requires_verification"
                            for item in result["entries"]))
        from app.services.hbi.schemas import LegalContextVerificationRequest
        verified = self.service.verify_legal_context(LegalContextVerificationRequest(
            topic="popia_section_27_research", verified_by="counsel",
            reference="written opinion 2026-11-27",
        ))
        self.assertEqual(verified["status"], "verified")

    async def test_partnership_records_training_rights(self):
        from app.services.hbi.schemas import PartnershipRequest
        result = self.service.add_partnership(PartnershipRequest(
            organisation="University", requested_rights=["read", "model_training"],
        ))
        self.assertTrue(result["requires_explicit_training_rights"])
        self.assertEqual(self.service.list_partnerships()["count"], 1)

    async def test_training_requires_independent_approval(self):
        from app.services.hbi.schemas import (
            CorpusReviewRequest, TrainingApprovalRequest, TrainingRequest,
        )
        review = self.service.review_corpus_source(CorpusReviewRequest(
            manifest=self._manifest(), intended_purpose="research",
            approved_by="ingestion-reviewer",
        ))
        self.assertEqual(review["decision"], "approved")
        self.service.request_training(TrainingRequest(source_id="SRC-PERM", intended_model="m1"))
        same = self.service.approve_training(TrainingApprovalRequest(
            source_id="SRC-PERM", approver="ingestion-reviewer",
            decision="approved", basis="same reviewer",
        ))
        self.assertEqual(same["decision"], "rejected")
        self.assertIn("independent_approver_required", same["blockers"])
        independent = self.service.approve_training(TrainingApprovalRequest(
            source_id="SRC-PERM", approver="training-reviewer",
            decision="approved", basis="training rights in agreement",
        ))
        self.assertEqual(independent["decision"], "approved")
        self.assertIn("SRC-PERM", self.service.training_approved()["sources"])

    async def test_training_blocked_without_training_rights(self):
        from app.services.hbi.schemas import (
            CorpusReviewRequest, TrainingApprovalRequest, TrainingRequest,
        )
        self.service.review_corpus_source(CorpusReviewRequest(
            manifest=self._manifest(training=False), intended_purpose="research",
            approved_by="ingestion-reviewer",
        ))
        self.service.request_training(TrainingRequest(source_id="SRC-PERM", intended_model="m1"))
        result = self.service.approve_training(TrainingApprovalRequest(
            source_id="SRC-PERM", approver="training-reviewer",
            decision="approved", basis="research access",
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("model_training_not_permitted", result["blockers"])

    async def test_restriction_removes_training_eligibility(self):
        from app.services.hbi.schemas import (
            CorpusRestrictionRequest, CorpusReviewRequest,
            TrainingApprovalRequest, TrainingRequest,
        )
        self.service.review_corpus_source(CorpusReviewRequest(
            manifest=self._manifest(), approved_by="ingestion-reviewer",
        ))
        self.service.request_training(TrainingRequest(source_id="SRC-PERM", intended_model="m1"))
        self.service.approve_training(TrainingApprovalRequest(
            source_id="SRC-PERM", approver="training-reviewer",
            decision="approved", basis="agreement",
        ))
        self.service.restrict_corpus_source(CorpusRestrictionRequest(
            source_id="SRC-PERM", reason="permission withdrawn",
        ))
        self.assertNotIn("SRC-PERM", self.service.training_approved()["sources"])


class HBIResearchEcosystemTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    def _manifest(self):
        from app.services.hbi.schemas import CorpusSourceManifest
        return CorpusSourceManifest(
            source_id="ECO-1", rights_holder="Institute",
            acquisition_method="open_access",
            source={"title": "Study", "origin": "https://example.org",
                    "collection_date": "2026-11-27"},
            licensing={
                "licence_id": "CC-BY-4.0",
                "licence_url": "https://creativecommons.org/licenses/by/4.0/",
                "permission_evidence": "licence",
                "ingestion_allowed": True, "storage_allowed": True,
                "analysis_allowed": True, "derivative_allowed": True,
                "model_training_allowed": True,
            },
            permitted_purposes=["research", "historical", "aggregate_analysis"],
        )

    async def _approved_source(self):
        from app.services.hbi.schemas import CorpusReviewRequest
        return self.service.review_corpus_source(CorpusReviewRequest(
            manifest=self._manifest(), approved_by="ingestion-reviewer",
        ))

    async def test_channels_and_targets(self):
        from app.services.hbi.schemas import TargetVerificationRequest
        self.assertEqual(self.service.acquisition_channels()["count"], 12)
        targets = self.service.discovery_targets()
        self.assertTrue(all(t["terms_status"] == "requires_verification" for t in targets["targets"]))
        verified = self.service.verify_target(TargetVerificationRequest(
            name="openalex", verified_by="counsel", reference="terms review 2026",
        ))
        self.assertEqual(verified["terms_status"], "verified")

    async def test_classification_and_enforcement(self):
        from app.services.hbi.schemas import (
            TrainingApprovalRequest, TrainingRequest,
        )
        await self._approved_source()
        self.assertEqual(self.service.source_classification("ECO-1")["classification"], "B")
        self.assertFalse(self.service.enforce("ECO-1", "training")["permitted"])
        self.assertTrue(self.service.enforce("ECO-1", "analysis")["permitted"])
        self.service.request_training(TrainingRequest(source_id="ECO-1", intended_model="m"))
        self.service.approve_training(TrainingApprovalRequest(
            source_id="ECO-1", approver="training-reviewer",
            decision="approved", basis="training rights granted",
        ))
        self.assertEqual(self.service.source_classification("ECO-1")["classification"], "A")
        self.assertTrue(self.service.enforce("ECO-1", "training")["permitted"])

    async def test_contribution_and_lab_ethics(self):
        from app.services.hbi.schemas import ContributionRequest, LabProjectRequest
        contribution = self.service.add_contribution(ContributionRequest(
            contributor="researcher", material_type="scenario",
            personal_data_present=True,
        ))
        self.assertEqual(contribution["status"], "quarantined")
        self.assertTrue(contribution["requires_ethics_review"])
        lab = self.service.lab_project(LabProjectRequest(
            title="Decision study", research_question="How do people decide?",
            human_participants=True,
        ))
        self.assertEqual(lab["status"], "blocked")
        self.assertIn("ethics_approval_required", lab["reason"])

    async def test_federated_analysis_is_result_only(self):
        from app.services.hbi.schemas import FederatedApprovalRequest, FederatedRequest
        request = self.service.federated_request(FederatedRequest(
            institution="university", analysis_description="aggregate statistics",
        ))
        self.assertFalse(request["raw_data_transfer"])
        self.assertTrue(request["result_only"])
        approved = self.service.federated_approve(FederatedApprovalRequest(
            institution="university", approver="reviewer", reference="agreement",
        ))
        self.assertEqual(approved["status"], "approved")

    async def test_transformation_respects_classification(self):
        from app.services.hbi.schemas import TransformationRequest
        result = self.service.transform(TransformationRequest(
            source_ids=["unknown"], output_type="knowledge_graph",
        ))
        self.assertFalse(result["permitted"])
        self.assertIn("unknown", result["blocked_sources"])


class HBITranslationLabTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = HBIService()

    async def test_translation_preserves_original_and_provenance(self):
        from app.services.hbi.schemas import TranslationRequest
        self.service.translation.translator = lambda text, source, target: f"[{target}] {text}"
        result = await self.service.translate(TranslationRequest(
            text="People in the community trusted the announcement.",
            source_language="en", target_language="fr", purpose="research",
        ))
        self.assertEqual(result["status"], "translated")
        self.assertEqual(result["engine"], "injected_translator")
        self.assertTrue(result["original_preserved"].startswith("People"))

    async def test_translation_fails_closed_without_engine(self):
        from app.services.hbi.schemas import TranslationRequest
        self.service.translation.inference = None
        result = await self.service.translate(TranslationRequest(
            text="People responded together.", purpose="research",
        ))
        self.assertEqual(result["status"], "not_performed")
        self.assertEqual(result["reason"], "no_translation_engine_configured")

    async def test_multilingual_semantics(self):
        from app.services.hbi.schemas import MultilingualSemanticsRequest
        self.service.translation.translator = lambda text, source, target: (
            "Community trust increased after the programme and people cooperated."
        )
        result = await self.service.multilingual_semantics(MultilingualSemanticsRequest(
            text="Die gemeenskap se vertroue het toegeneem en mense het saamgewerk.",
            region="south_africa", purpose="research",
        ))
        self.assertIn("south_african_context", result["cultural_tags"])
        self.assertTrue(result["translated_claims"])

    async def test_study_lifecycle_with_consent_and_deletion(self):
        from app.services.hbi.schemas import (
            ParticipantConsentRequest, ParticipantWithdrawalRequest,
            StudyCreateRequest, StudyResponseRequest,
        )
        blocked = self.service.create_study(StudyCreateRequest(
            title="Study", research_question="How do people decide?",
        ))
        self.assertEqual(blocked["status"], "blocked")
        study = self.service.create_study(StudyCreateRequest(
            title="Study", research_question="How do people decide?",
            ethics_reference="ethics-1",
        ))
        sid = study["study_id"]
        denied = self.service.collect_response(StudyResponseRequest(
            study_id=sid, participant_ref="p1", response="I trusted the message.",
        ))
        self.assertEqual(denied["status"], "rejected")
        consent = self.service.record_consent(ParticipantConsentRequest(
            study_id=sid, participant_ref="p1", purposes=["research"],
        ))
        self.assertEqual(consent["status"], "active")
        response = self.service.collect_response(StudyResponseRequest(
            study_id=sid, participant_ref="p1", response="I trusted the message.",
        ))
        self.assertEqual(response["status"], "stored")
        self.assertNotEqual(response["pseudonym"], "p1")
        withdrawal = self.service.withdraw_participant(ParticipantWithdrawalRequest(
            study_id=sid, participant_ref="p1",
        ))
        self.assertTrue(withdrawal["deletion_required"])
        deleted = self.service.delete_study_responses(sid, "p1")
        self.assertEqual(deleted["responses_removed"], 1)
        report = self.service.study_report(sid)
        self.assertEqual(report["deleted_responses"], 1)


if __name__ == "__main__":
    unittest.main()
