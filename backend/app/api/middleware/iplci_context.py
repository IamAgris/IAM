"""Establish IPLCI governance context once per HTTP request.

Protected headers:
    X-IPLCI-Source-Id       registered IPLCI source identifier
    X-IPLCI-Dataset-Id      training dataset identifier
    X-IPLCI-Approval-Id     independent training approval identifier
    X-IPLCI-Agent-Id        calling agent identity
    X-IPLCI-Jurisdiction    applicable jurisdiction

When a source id is present, every downstream IPLCI-aware service inherits the
context even if it does not pass an explicit argument. Requests without these
headers are unchanged.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.services.iplci.context import governance_context


class IPLCIContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        context: Dict[str, Any] = {}
        header_map = {
            "x-iplci-source-id": "source_id",
            "x-iplci-dataset-id": "dataset_id",
            "x-iplci-approval-id": "approval_id",
            "x-iplci-agent-id": "agent_id",
            "x-iplci-jurisdiction": "jurisdiction",
        }
        for header, key in header_map.items():
            value = request.headers.get(header)
            if value:
                context[key] = value
        async with governance_context(context):
            return await call_next(request)
