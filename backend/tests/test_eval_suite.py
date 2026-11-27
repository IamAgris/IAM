"""Representative multi-domain evaluation with thresholds and regression checks."""

import json
import unittest
from pathlib import Path

from app.services.ai_research.base import ResearchError
from app.services.ai_research.benchmarks import BenchmarkSpec
from app.services.ai_research.lm_eval import EvaluationSuite, default_eval_suite


SET_DIR = Path(__file__).resolve().parents[1] / "app" / "services" / "ai_research" / "eval_sets"


def expected_by_prompt():
    answers = {}
    for path in SET_DIR.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                answers[record["prompt"]] = record["expected"]
    return answers


class CorrectClient:
    def __init__(self, *_args, **_kwargs):
        self.answers = expected_by_prompt()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, _url, json):
        answer = self.answers.get(json["prompt"], "WRONG")
        return type("Response", (), {"status_code": 200, "json": lambda self: {"response": answer}})()


class BrokenSafetyClient(CorrectClient):
    def post(self, url, json):
        if "refuse" in self.answers.get(json["prompt"], "") or json["prompt"].startswith(("A user asks", "A document", "A peer")):
            return type("Response", (), {"status_code": 200, "json": lambda self: {"response": "proceed"}})()
        return super().post(url, json)


SPEC = BenchmarkSpec(name="capability-suite", task_type="reasoning")


class EvalSuiteTests(unittest.TestCase):
    def test_suite_has_representative_domains_and_thresholds(self):
        suite = EvaluationSuite(client_factory=CorrectClient)
        names = {item["name"] for item in suite.suites}
        self.assertEqual(
            names,
            {"reasoning", "planning", "tool_use", "safety", "instruction_following"},
        )
        self.assertTrue(all(item["threshold"] > 0 for item in suite.suites))

    def test_suite_scores_each_domain_and_passes(self):
        suite = EvaluationSuite(client_factory=CorrectClient)
        report = suite.evaluate_detailed(SPEC, "local-qwen-coder-3b")
        self.assertEqual(len(report["domains"]), 5)
        self.assertEqual(report["overall_score"], 1.0)
        self.assertTrue(report["passed"])
        self.assertTrue(all(len(item["dataset_sha256"]) == 64 for item in report["domains"].values()))

    def test_domain_below_threshold_fails_the_suite(self):
        suite = EvaluationSuite(client_factory=BrokenSafetyClient)
        report = suite.evaluate_detailed(SPEC, "candidate")
        self.assertFalse(report["domains"]["safety"]["passed"])
        self.assertFalse(report["passed"])

    def test_regression_comparison_detects_domain_drop(self):
        baseline = {"reasoning": {"score": 0.9}, "safety": {"score": 1.0}}
        candidate = {"reasoning": {"score": 0.7}, "safety": {"score": 1.0}}
        result = EvaluationSuite.compare(baseline, candidate)
        self.assertFalse(result["passed"])
        self.assertEqual(result["regressions"][0]["domain"], "reasoning")

    def test_invalid_manifest_fails_closed(self):
        with self.assertRaises(ResearchError):
            EvaluationSuite("does-not-exist-manifest.json")

    def test_default_suite_is_available(self):
        self.assertIsInstance(default_eval_suite(client_factory=CorrectClient), EvaluationSuite)


if __name__ == "__main__":
    unittest.main()
