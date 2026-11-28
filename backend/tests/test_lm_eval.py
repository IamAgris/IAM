"""Trusted local evaluator: versioned eval set, deterministic exact match."""

import unittest
from unittest.mock import patch

from app.core.config import settings
from app.services.ai_research import lm_eval
from app.services.ai_research.base import ResearchError
from app.services.ai_research.benchmarks import BenchmarkSpec


class FakeResponse:
    status_code = 200

    def __init__(self, answer):
        self.answer = answer

    def json(self):
        return {"response": self.answer}


class FakeClient:
    responses = iter(["IAM", "4", "Paris", "seven", "Mars"])

    def __init__(self, *_args, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, _url, json):
        return FakeResponse(next(self.responses))


class LMEvalTests(unittest.TestCase):
    def test_default_driver_loads_versioned_eval_set(self):
        driver = lm_eval.default_lm_eval_driver()
        self.assertIsNotNone(driver)
        self.assertEqual(len(driver.records), 5)
        self.assertEqual(len(driver.checksum), 64)

    def test_exact_match_scoring_is_deterministic(self):
        FakeClient.responses = iter(["IAM", "4", "Paris", "seven", "Mars"])
        driver = lm_eval.default_lm_eval_driver()
        spec = BenchmarkSpec(name="test", task_type="coding")
        with patch.object(lm_eval.httpx, "Client", FakeClient):
            score = driver.evaluate(spec, "local-qwen-coder-3b")
        self.assertAlmostEqual(score, 0.8)

    def test_missing_dataset_fails_closed(self):
        with self.assertRaises(ResearchError):
            lm_eval.OllamaLMEvalDriver("does-not-exist.jsonl")

    def test_eval_checksum_is_part_of_benchmark_config(self):
        driver = lm_eval.default_lm_eval_driver()
        config = lm_eval.eval_config(driver)
        self.assertEqual(config["dataset_sha256"], driver.checksum)


if __name__ == "__main__":
    unittest.main()
