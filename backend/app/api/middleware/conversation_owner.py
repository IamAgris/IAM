"""Server-issued conversation ownership for public chat routes.

An anonymous, HttpOnly cookie identifies the browser that created a
conversation. No client code change is needed: the browser sends the cookie
automatically on subsequent chat and conversation requests. An authenticated
credential, when present, is not replaced — it is a stronger identity and is
used instead by :func:`conversation_owner`.
"""

import uuid
from typing import Any, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import settings

COOKIE_NAME = "iam_conversation_owner"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365


def _is_uuid(value: str) -> bool:
    try:
        return bool(uuid.UUID(value))
    except (ValueError, AttributeError, TypeError):
        return False


class ConversationOwnerMiddleware(BaseHTTPMiddleware):
    """Ensure every request has a stable, server-issued owner token."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        token = str(request.cookies.get(COOKIE_NAME, "")).strip()
        issued = not _is_uuid(token)
        if issued:
            token = str(uuid.uuid4())
        request.state.conversation_owner = token
        response = await call_next(request)
        if issued:
            response.set_cookie(
                COOKIE_NAME,
                token,
                max_age=COOKIE_MAX_AGE,
                httponly=True,
                samesite="lax",
                secure=settings.app_env == "production",
            )
        return response


def cookie_owner(request: Request) -> Optional[str]:
    """The raw anonymous cookie owner, regardless of any credential."""
    if request is None:
        return None
    state = getattr(request, "state", None)
    token = getattr(state, "conversation_owner", None) if state is not None else None
    return str(token) if token else None


def conversation_owner(request: Request) -> Optional[str]:
    """Return the owner token attached to this request, if middleware ran."""
    if request is None:
        return None
    state = getattr(request, "state", None)
    if state is None:
        return None
    credential = getattr(state, "credential", None)
    if isinstance(credential, dict) and credential.get("id"):
        return f"credential:{credential['id']}"
    token = getattr(state, "conversation_owner", None)
    return str(token) if token else None
