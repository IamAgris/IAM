"""Request correlation id and structured logging context.

Every request gets a stable id (inbound X-Request-Id or a new UUID4), exposed
as X-Request-ID on the response and bound to loguru records. This lets runtime
logs be correlated with the audit events and RKIE evidence records.
"""

import uuid
from contextvars import ContextVar
from typing import Any

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

request_id_var: ContextVar[str] = ContextVar("iam_request_id", default="-")


def _patch(record: Any) -> None:
    record["extra"]["request_id"] = request_id_var.get()


logger.configure(patcher=_patch)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("x-request-id", "").strip() or str(uuid.uuid4())
        token = request_id_var.set(request_id)
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response
