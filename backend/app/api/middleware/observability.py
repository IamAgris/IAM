"""HTTP tracing and metrics middleware.

Request IDs are handled by RequestContextMiddleware; this layer adds a span
per request and feeds the counters exposed at /metrics.
"""

import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.observability import metrics, span


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.monotonic()
        metrics.begin()
        status = 500
        try:
            with span(
                "http.request",
                http_method=request.method,
                http_route=request.url.path,
            ):
                response = await call_next(request)
                status = response.status_code
                return response
        finally:
            metrics.finish(status, time.monotonic() - start)
