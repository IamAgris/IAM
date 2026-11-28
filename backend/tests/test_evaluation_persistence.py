"""Evaluation results must be persisted and read back correctly.

Both the self-evaluation and independent-evaluation suites store reports in
IAM's shared epistemic state. ``get_belief_state`` returns detached
``BeliefRecord`` objects whose payload is the ``evidence`` list, so reading from
a ``metadata_`` attribute silently loses every stored report.
"""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.orchestration.evaluation_suite import (
    DomainResult,
    EvaluationReport,
    LongitudinalEvaluator,
)
from app.orchestration.independent_evaluation import (
    DomainResult as IndependentDomainResult,
    EvaluationReport as IndependentReport,
    IndependentEvaluator,
)


class SelfEvaluationPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_store_report_serializes_the_full_report(self):
        report = EvaluationReport(
            run_id="run-1",
            model="qwen2.5:3b",
            overall_score=0.8,
            overall_passed=True,
            domains=[
                DomainResult("reasoning", 0.8, 10, 8, 0.7, True, "sha")
            ],
            created_at="2026-11-27T10:00:00+00:00",
        )
        evaluator = LongitudinalEvaluator(SimpleNamespace())
        with patch(
            "app.services.iam_context.record_belief", new=AsyncMock()
        ) as record, patch.object(evaluator.db, "commit", new=AsyncMock(), create=True):
            await evaluator.store_report(report)

        record.assert_awaited_once()
        content = json.loads(record.await_args.kwargs["content"])
        self.assertEqual(content["run_id"], "run-1")
        self.assertEqual(content["domains"][0]["domain"], "reasoning")

    async def test_previous_reports_are_read_from_belief_evidence(self):
        stored = {
            "type": "evaluation_report",
            "run_id": "run-1",
            "overall_score": 0.8,
            "overall_passed": True,
            "created_at": "2026-11-27T10:00:00+00:00",
            "domains": {"reasoning": {"score": 0.8, "passed": True}},
        }
        belief = SimpleNamespace(belief_type="measurement", evidence=[stored])
        evaluator = LongitudinalEvaluator(SimpleNamespace())
        with patch(
            "app.services.iam_context.get_belief_state",
            new=AsyncMock(return_value=[belief]),
        ):
            reports = await evaluator._get_previous_reports(limit=1)

        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].run_id, "run-1")
        self.assertEqual(reports[0].domains[0].domain, "reasoning")


class IndependentEvaluationPersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_evaluation_stores_and_compares(self):
        report = IndependentReport(
            run_id="ind-1",
            timestamp="2026-11-27T10:00:00+00:00",
            iam_base_url="http://iam:8000",
            overall_score=0.6,
            overall_passed=False,
            domains=[
                IndependentDomainResult("reasoning", 0.6, 10, 6, 0.7, False, "sha")
            ],
        )
        evaluator = IndependentEvaluator(SimpleNamespace())
        with (
            patch.object(
                evaluator, "evaluate_domain", new=AsyncMock(return_value=report.domains[0])
            ),
            patch.object(
                evaluator, "compare_to_iam_self_eval", new=AsyncMock(return_value=None)
            ) as compare,
            patch.object(evaluator, "store_report", new=AsyncMock()) as store,
            patch.object(evaluator, "_load_manifest", new=AsyncMock(return_value={
                "suites": [{"name": "reasoning", "threshold": 0.7}]
            })),
            patch.object(evaluator, "_load_records", new=AsyncMock(return_value={
                "reasoning": []
            })),
        ):
            result = await evaluator.run_full_evaluation()

        compare.assert_awaited_once()
        store.assert_awaited_once_with(result)
        self.assertTrue(result.run_id)
        self.assertEqual(len(result.domains), 1)
        self.assertEqual(result.domains[0].domain, "reasoning")


class SelfEvalLeniencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_independent_report_is_compared_to_iam_self_evaluation(self):
        from app.orchestration.independent_evaluation import IndependentEvaluator

        self_belief = SimpleNamespace(
            belief_type="measurement",
            evidence=[{
                "type": "evaluation_report",
                "run_id": "self-run-1",
                "created_at": "2026-11-27T10:00:00+00:00",
                "overall_score": 0.9,
                "domains": {"reasoning": {"score": 0.9, "passed": True}},
            }],
        )
        independent = IndependentReport(
            run_id="ind-1",
            timestamp="2026-11-27T11:00:00+00:00",
            iam_base_url="http://iam:8000",
            overall_score=0.6,
            overall_passed=False,
            domains=[
                IndependentDomainResult("reasoning", 0.6, 10, 6, 0.7, False, "sha")
            ],
        )
        evaluator = IndependentEvaluator(SimpleNamespace())
        with patch(
            "app.services.iam_context.get_belief_state",
            new=AsyncMock(return_value=[self_belief]),
        ):
            result = await evaluator.compare_to_iam_self_eval(independent)

        self.assertIsNotNone(result)
        self.assertEqual(result["iam_self_eval_run_id"], "self-run-1")
        self.assertEqual(result["leniency"], "lenient")
        self.assertEqual(result["overall_delta"], -0.3)
        self.assertEqual(
            result["domain_comparisons"]["reasoning"]["leniency"], "lenient"
        )

    async def test_no_self_evaluation_returns_no_comparison(self):
        from app.orchestration.independent_evaluation import IndependentEvaluator

        evaluator = IndependentEvaluator(SimpleNamespace())
        with patch(
            "app.services.iam_context.get_belief_state",
            new=AsyncMock(return_value=[]),
        ):
            result = await evaluator.compare_to_iam_self_eval(
                IndependentReport(
                    run_id="ind-1",
                    timestamp="2026-11-27T11:00:00+00:00",
                    iam_base_url="http://iam:8000",
                    overall_score=0.6,
                    overall_passed=False,
                    domains=[],
                )
            )
        self.assertIsNone(result)


class IndependentIntegrityTests(unittest.IsolatedAsyncioTestCase):
    async def test_tampered_report_is_not_admitted_as_evidence(self):
        from app.orchestration.independent_evaluation import IndependentEvaluator

        payload = {
            "type": "evaluation_report",
            "run_id": "ind-1",
            "iam_base_url": "http://iam:8000",
            "overall_score": 0.6,
            "overall_passed": False,
            "domains": {"reasoning": {"score": 0.6, "passed": False}},
            "timestamp": "2026-11-27T10:00:00+00:00",
        }
        digest = IndependentEvaluator._chain_hash("", payload)
        good = SimpleNamespace(
            belief_type="measurement",
            evidence=[{
                **payload,
                "integrity": {"previous_hash": "", "hash": digest},
            }],
        )
        tampered = SimpleNamespace(
            belief_type="measurement",
            evidence=[{
                **payload,
                "overall_score": 0.99,
                "integrity": {"previous_hash": "", "hash": digest},
            }],
        )
        evaluator = IndependentEvaluator(SimpleNamespace())
        with patch(
            "app.services.iam_context.get_belief_state",
            new=AsyncMock(side_effect=[[good], [tampered]]),
        ):
            accepted = await evaluator._get_previous_reports(limit=1)
            rejected = await evaluator._get_previous_reports(limit=1)

        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0].integrity_hash, digest)
        self.assertEqual(rejected, [])


class ExternalEvidenceStoreTests(unittest.TestCase):
    def test_append_once_and_signature_detects_tampering(self):
        import tempfile

        from app.services.independent_evidence_store import IndependentEvidenceStore

        with tempfile.TemporaryDirectory() as root:
            store = IndependentEvidenceStore(root=root, signing_key="operator-secret")
            payload = {"run_id": "ind-1", "overall_score": 0.6, "domains": []}
            signature = store.append("ind-1", payload)
            self.assertTrue(store.verify("ind-1", payload, signature))
            with self.assertRaises(FileExistsError):
                store.append("ind-1", payload)

            path = store.root / "ind-1.json"
            path.write_bytes(b'{"run_id": "ind-1", "overall_score": 0.99}')
            self.assertFalse(store.verify("ind-1", payload, signature))


if __name__ == "__main__":
    unittest.main()
