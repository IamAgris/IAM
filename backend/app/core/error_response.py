"""Uniform API error envelope.

IAM_API_CONTRACTS.md:16 requires every error body to carry
``detail``, ``code`` and ``request_id``. Existing clients may still read the
legacy ``error`` field, so callers can pass it as an extra field.
"""

from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse


def request_id_for(request: Request) -> str:
    """Return a stable per-request id, preferring an inbound X-Request-Id."""
    existing = getattr(request.state, "request_id", None)
    if existing:
        return str(existing)
    value = request.headers.get("x-request-id") or str(uuid4())
    request.state.request_id = value
    return value


def error_response(
    *,
    request: Request,
    status_code: int,
    detail: str,
    code: str,
    headers: Optional[Dict[str, str]] = None,
    **extra: Any,
) -> JSONResponse:
    """Build a contract-compliant JSON error response."""
    payload: Dict[str, Any] = {
        "detail": detail,
        "code": code,
        "request_id": request_id_for(request),
    }
    payload.update(extra)
    return JSONResponse(status_code=status_code, content=payload, headers=headers)
