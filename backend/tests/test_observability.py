"""Runtime observability must expose counters and safe spans without an SDK."""

import unittest

from app.core.observability import metrics, prometheus_text, span


class ObservabilityTests(unittest.TestCase):
    def test_span_is_safe_without_sdk(self):
        with span("test.span", component="unit") as active:
            active.set_attribute("safe", "yes")
            active.record_exception(ValueError("ignored"))

    def test_metrics_reflect_requests_and_errors(self):
        before = metrics.snapshot()
        metrics.begin()
        metrics.finish(200, 0.01)
        metrics.begin()
        metrics.finish(503, 0.02)
        after = metrics.snapshot()
        self.assertEqual(after["requests"] - before["requests"], 2)
        self.assertEqual(after["errors"] - before["errors"], 1)
        self.assertEqual(after["in_flight"], before["in_flight"])

    def test_prometheus_text_exposes_alertable_signals(self):
        text = prometheus_text()
        for name in (
            "iam_http_requests_total",
            "iam_http_errors_total",
            "iam_http_in_flight",
            "iam_http_request_seconds_sum",
        ):
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
