"""Provider compatibility diagnostics, recorded without secrets.

A schema rejection is a recorded compatibility fact, never a silent downgrade
that is later reported as a successful tool execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import loguru
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import AuditEvent

logger = loguru.logger


@dataclass(frozen=True)
class CompatibilityResult:
    provider: str
    model: str
    check: str
    status: str  # accepted | rejected | unsupported
    http_status: Optional[int] = None
    detail: str = ""


def redact_detail(text: str, limit: int = 300) -> str:
    """Bound provider error text; never include credentials or message bodies."""
    cleaned = " ".join(str(text or "").split())
    return cleaned[:limit]


def as_dict(result: CompatibilityResult) -> Dict[str, Any]:
    return {
        "provider": result.provider,
        "model": result.model,
        "check": result.check,
        "status": result.status,
        "http_status": result.http_status,
        "detail": redact_detail(result.detail),
    }


async def record_result(
    db: Optional[AsyncSession], result: CompatibilityResult
) -> bool:
    """Record a compatibility check as a durable audit event."""
    payload = as_dict(result)
    logger.info(f"provider.compatibility {payload['provider']}/{payload['model']} "
                f"{result.check}={result.status}")
    if db is None:
        return False
    try:
        db.add(
            AuditEvent(
                event_type="provider.compatibility",
                actor="iam",
                target=f"{result.provider}/{result.model}",
                details=payload,
            )
        )
        await db.flush()
        return True
    except Exception as exc:  # diagnostics must never break inference
        logger.warning(f"Compatibility diagnostic not persisted: {type(exc).__name__}")
        return False
