"""Admin-gated provider compatibility probes (OD-38/46/52)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.provider_compat import run_compatibility_probes

router = APIRouter(prefix="/api/v1/provider-compat", tags=["provider-compat"])


class ProbeRequest(BaseModel):
    provider: str
    model: str
    retries: int = 0
    retry_delay_seconds: int = 60


@router.post("/probe")
async def probe_model(
    payload: ProbeRequest, db: AsyncSession = Depends(get_db_session)
) -> Dict[str, Any]:
    """Run and persist the compatibility probe matrix for one model."""
    results = await run_compatibility_probes(
        db,
        payload.provider,
        payload.model,
        retries=payload.retries,
        retry_delay_seconds=payload.retry_delay_seconds,
    )
    return {
        "provider": payload.provider,
        "model": payload.model,
        "results": [item.as_dict() for item in results],
        "passed": sum(1 for item in results if item.status == "accepted"),
        "total": len(results),
    }
