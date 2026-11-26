"""Operational endpoints documented in IAM_API_CONTRACTS.md section 11.

These routes are intentionally outside the /api/v1 namespace: the contract
specifies /health, /health/ready, /health/live and /metrics.
"""

import time

from fastapi import APIRouter
from fastapi.responses import JSONResponse, PlainTextResponse
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine

router = APIRouter()

_STARTED_AT = time.monotonic()


@router.get("/health/live")
async def health_live() -> dict:
    """Liveness only — no dependency checks."""
    return {"status": "alive", "service": "aura-backend"}


@router.get("/health/ready")
async def health_ready() -> JSONResponse:
    """Readiness: database and Redis; model gateway is reported, not required.

    Offline operation is an approved IAM mode, so an unavailable model gateway
    does not make the process unready.
    """
    components = {}
    db_ok = False
    redis_ok = False

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # pragma: no cover - depends on live infrastructure
        components["database"] = type(exc).__name__

    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=1)
        try:
            await client.ping()
            redis_ok = True
        finally:
            await client.aclose()
    except Exception as exc:  # pragma: no cover - depends on live infrastructure
        components["redis"] = type(exc).__name__

    components["database"] = "ok" if db_ok else components.get("database", "unavailable")
    components["redis"] = "ok" if redis_ok else components.get("redis", "unavailable")
    components["model_gateway"] = (
        "configured" if settings.litellm_base_url else "unavailable"
    )

    ready = db_ok and redis_ok
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "service": "aura-backend",
            "components": components,
        },
    )


@router.get("/metrics")
async def metrics() -> PlainTextResponse:
    """Minimal Prometheus-format process metrics, with no external dependency."""
    import gc

    lines = [
        "# HELP iam_up Whether the IAM backend process is running.",
        "# TYPE iam_up gauge",
        "iam_up 1",
        "# HELP iam_uptime_seconds Process uptime in seconds.",
        "# TYPE iam_uptime_seconds gauge",
        f"iam_uptime_seconds {time.monotonic() - _STARTED_AT:.3f}",
        "# HELP iam_python_gc_objects Objects tracked by the Python garbage collector.",
        "# TYPE iam_python_gc_objects gauge",
        f"iam_python_gc_objects {len(gc.get_objects())}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
