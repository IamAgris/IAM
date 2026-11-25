"""API authentication and rate limiting middleware.

Public routes (health, docs, global access and the HMAC-protected Creator
gateway) pass through. All other routes require a scoped API credential.
Creator authority is unaffected: an admin key can call Creator endpoints but
cannot create approval or authorization without a signed challenge.
"""

from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.auth_policy import has_scope, required_scope
from app.core.config import settings
from app.core.database import get_session_factory
from app.core.rate_limit import RateLimiter, RedisRateLimiter
from app.services.auth_service import AuthService


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.local_limiter = RateLimiter(settings.auth_rate_limit_per_minute)
        self.redis_limiter = (
            RedisRateLimiter(settings.redis_url, settings.auth_rate_limit_per_minute)
            if settings.rate_limit_backend.lower() == "redis"
            else None
        )

    async def _rate_check(self, key: str):
        if self.redis_limiter:
            try:
                return await self.redis_limiter.check(key)
            except Exception:
                # Fall back to local state if Redis is temporarily unavailable.
                return self.local_limiter.check(key)
        return self.local_limiter.check(key)

    async def _authenticate(self, request: Request) -> Optional[Dict[str, Any]]:
        header = request.headers.get("authorization", "")
        if header.lower().startswith("bearer "):
            key = header[7:].strip()
        else:
            key = request.headers.get("x-api-key", "").strip()
        if not key:
            return None
        async with get_session_factory()() as db:
            return await AuthService(db).verify_key(key)

    async def dispatch(self, request: Request, call_next):
        if not settings.auth_enabled:
            return await call_next(request)

        required = required_scope(request.url.path)
        if required is None:
            return await call_next(request)

        credential = await self._authenticate(request)
        if credential is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid API credential"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not has_scope(credential["scope"], required):
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        f"Credential scope '{credential['scope']}' is insufficient; "
                        f"'{required}' required"
                    )
                },
            )

        client = request.client.host if request.client else "unknown"
        allowed, retry_after = await self._rate_check(f"{credential['id']}:{client}")
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )

        request.state.credential = credential
        return await call_next(request)
