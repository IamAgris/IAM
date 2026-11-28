"""Dependency-light tracing and runtime metrics for IAM.

OTLP export is enabled when an OpenTelemetry SDK is configured in the
deployment; the API-only install used in development yields safe no-op spans.
Counters are always available and are exposed through ``/metrics`` so a
deployment can alert on request volume, errors and latency without an
external agent.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from typing import Any, Dict, Iterator

try:  # pragma: no cover - depends on optional SDK
    from opentelemetry import trace as _otel_trace

    _tracer: Any = _otel_trace.get_tracer("iam.backend")
except Exception:  # pragma: no cover
    _tracer = None


class _NoopSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def record_exception(self, exc: BaseException) -> None:
        return None


@contextmanager
def span(name: str, **attributes: Any) -> Iterator[Any]:
    """Open a span when tracing is configured, otherwise a harmless no-op."""
    if _tracer is None:
        yield _NoopSpan()
        return
    with _tracer.start_as_current_span(name) as active:
        for key, value in attributes.items():
            active.set_attribute(key, str(value))
        yield active


class _Metrics:
    """Thread-safe counters shared by middleware and the metrics endpoint."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.started = time.time()
        self.requests = 0
        self.errors = 0
        self.in_flight = 0
        self.latency_sum = 0.0
        self.requests_by_status: Dict[str, int] = defaultdict(int)

    def begin(self) -> None:
        with self._lock:
            self.in_flight += 1

    def finish(self, status: int, elapsed: float) -> None:
        with self._lock:
            self.in_flight = max(0, self.in_flight - 1)
            self.requests += 1
            self.latency_sum += elapsed
            self.requests_by_status[f"{status // 100}xx"] += 1
            if status >= 500:
                self.errors += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "requests": self.requests,
                "errors": self.errors,
                "in_flight": self.in_flight,
                "latency_sum": self.latency_sum,
                "by_status": dict(self.requests_by_status),
            }


metrics = _Metrics()


def prometheus_text() -> str:
    """Prometheus exposition for request/health alerting."""
    data = metrics.snapshot()
    requests = data["requests"]
    errors = data["errors"]
    lines = [
        "# HELP iam_http_requests_total Requests handled by the backend.",
        "# TYPE iam_http_requests_total counter",
        f"iam_http_requests_total {requests}",
        "# HELP iam_http_errors_total Responses with a 5xx status.",
        "# TYPE iam_http_errors_total counter",
        f"iam_http_errors_total {errors}",
        "# HELP iam_http_in_flight Requests currently being processed.",
        "# TYPE iam_http_in_flight gauge",
        f"iam_http_in_flight {data['in_flight']}",
        "# HELP iam_http_request_seconds_sum Cumulative request latency.",
        "# TYPE iam_http_request_seconds_sum counter",
        f"iam_http_request_seconds_sum {float(data['latency_sum']):.3f}",
    ]
    for bucket, count in sorted(data["by_status"].items()):
        lines.append(f'iam_http_responses_total{{status="{bucket}"}} {count}')
    return "\n".join(lines) + "\n"
