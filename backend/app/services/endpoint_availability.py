"""Free-endpoint availability monitoring (OD-52 Phase D).

A catalogue entry, a metadata record and a registered LiteLLM alias are all
still only claims. This monitor probes through the LiteLLM gateway with the
backend's master key and classifies failures. Paid endpoints are never probed.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
import loguru
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.modelrouter import DiscoveredModel

logger = loguru.logger


@dataclass(frozen=True)
class AvailabilityResult:
    model_id: str
    status: str  # available | auth | rate_limit | model_outage | network | unknown
    reason: str

    def as_dict(self) -> Dict[str, Any]:
        return {"model_id": self.model_id, "status": self.status, "reason": self.reason[:200]}


def classify(status_code: int) -> AvailabilityResult:
    """Translate a gateway/provider HTTP status into an operational class."""
    if 200 <= status_code < 300:
        return AvailabilityResult("", "available", "endpoint responded")
    if status_code in (401, 403):
        return AvailabilityResult("", "auth", "credential rejected")
    if status_code == 429:
        return AvailabilityResult("", "rate_limit", "shared quota or rate limit")
    if status_code in (404, 410):
        return AvailabilityResult("", "model_outage", "model retired or endpoint disabled")
    if status_code >= 500:
        return AvailabilityResult("", "model_outage", "provider/server failure")
    return AvailabilityResult("", "unknown", f"unexpected status {status_code}")


class EndpointAvailabilityMonitor:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check(self, alias: str, model_id: str) -> AvailabilityResult:
        if not settings.endpoint_availability_enabled:
            return AvailabilityResult(model_id, "unknown", "availability monitoring disabled")
        try:
            async with httpx.AsyncClient(timeout=settings.availability_probe_timeout_seconds) as client:
                response = await client.post(
                    f"{settings.litellm_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.litellm_master_key}"},
                    json={
                        "model": alias,
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                    },
                )
            result = classify(response.status_code)
        except httpx.HTTPError:
            result = AvailabilityResult(model_id, "network", "provider unreachable")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"Availability probe failed for {model_id}: {exc}")
            result = AvailabilityResult(model_id, "unknown", "probe failed")
        return AvailabilityResult(model_id, result.status, result.reason)

    async def monitor_all(self) -> List[Dict[str, Any]]:
        """Probe free registered models and persist the outcome."""
        if not settings.endpoint_availability_enabled:
            return []
        result = await self.db.execute(
            select(DiscoveredModel).where(
                DiscoveredModel.access_type == "free",
                DiscoveredModel.alias.isnot(None),
            )
        )
        rows = [row for row in result.scalars().all() if row.alias and row.access_type == "free"]
        semaphore = asyncio.Semaphore(max(1, settings.availability_probe_concurrency))

        async def one(row: DiscoveredModel) -> Dict[str, Any]:
            if not row.alias or row.access_type != "free":
                return AvailabilityResult(
                    str(row.model_id), "unknown", "not eligible for probing"
                ).as_dict()
            async with semaphore:
                outcome = await self.check(str(row.alias), str(row.model_id))
                now = datetime.now(timezone.utc)
                row.last_tested = now  # type: ignore[assignment]
                row.test_result = outcome.as_dict()  # type: ignore[assignment]
                row.endpoint_status = "available" if outcome.status == "available" else "unavailable"  # type: ignore[assignment]
                if outcome.status == "available":
                    row.last_known_good = {  # type: ignore[assignment]
                        "model_id": row.model_id,
                        "alias": row.alias,
                        "at": now.isoformat(),
                    }
                elif row.last_known_good is None:
                    row.last_known_good = {"model_id": row.model_id, "alias": row.alias, "tested": False}
                return outcome.as_dict()

        outcomes = await asyncio.gather(*(one(row) for row in rows))
        await self.db.flush()
        await self.db.commit()
        return list(outcomes)
