"""Unit tests for the competition harness's derived metrics.

Run directly: python -m pytest tests/model_competition/test_metrics.py -q
"""

import unittest

from metrics import derive_metrics


class DeriveMetricsTests(unittest.TestCase):
    def test_derives_decode_and_observed_prefill(self):
        result = derive_metrics(
            {
                "ttft_ms": 500.0,
                "latency_ms": 2500.0,
                "usage": {"prompt_tokens": 40, "completion_tokens": 100},
            }
        )
        self.assertEqual(result["prompt_tokens"], 40)
        self.assertEqual(result["completion_tokens"], 100)
        self.assertEqual(result["decode_tps"], 50.0)
        self.assertEqual(result["prefill_tps_observed"], 80.0)

    def test_missing_usage_yields_no_derived_numbers(self):
        result = derive_metrics({"ttft_ms": 500.0, "latency_ms": 2500.0})
        self.assertIsNone(result["prompt_tokens"])
        self.assertIsNone(result["completion_tokens"])
        self.assertIsNone(result["decode_tps"])
        self.assertIsNone(result["prefill_tps_observed"])

    def test_missing_ttft_yields_no_throughput(self):
        result = derive_metrics(
            {"latency_ms": 2500.0, "usage": {"prompt_tokens": 40, "completion_tokens": 100}}
        )
        self.assertIsNone(result["decode_tps"])
        self.assertIsNone(result["prefill_tps_observed"])

    def test_non_positive_durations_yield_none(self):
        result = derive_metrics(
            {
                "ttft_ms": 0.0,
                "latency_ms": 0.0,
                "usage": {"prompt_tokens": 40, "completion_tokens": 100},
            }
        )
        self.assertIsNone(result["decode_tps"])
        self.assertIsNone(result["prefill_tps_observed"])

    def test_latency_not_after_ttft_yields_no_decode_rate(self):
        result = derive_metrics(
            {
                "ttft_ms": 2500.0,
                "latency_ms": 2500.0,
                "usage": {"prompt_tokens": 40, "completion_tokens": 100},
            }
        )
        self.assertIsNone(result["decode_tps"])

    def test_malformed_usage_is_ignored(self):
        result = derive_metrics(
            {
                "ttft_ms": 500.0,
                "latency_ms": 2500.0,
                "usage": {"prompt_tokens": "40", "completion_tokens": None},
            }
        )
        self.assertIsNone(result["prompt_tokens"])
        self.assertIsNone(result["completion_tokens"])
        self.assertIsNone(result["decode_tps"])


if __name__ == "__main__":
    unittest.main()
