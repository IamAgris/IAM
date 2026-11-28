"""Fail-closed usage accounting for model inference (OD-51 §4.3).

A paid request is only allowed when authorisation, remaining budget and an
applicable cost limit can all be determined. If any of them is missing the
request is denied and the denial reason is recorded — never default-allowed.
The existing ProviderUsage and RequestUsage tables are the accounting record.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, cast
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.globalaccess import RequestUsage
from app.models.model_provider_key import ModelProviderKey
from app.models.modelrouter import AIProvider, DiscoveredModel, ProviderUsage


class UsageDenied(PermissionError):
    """Raised when a paid request cannot be proven authorised and affordable."""


@dataclass(frozen=True)
class UsageDecision:
    allowed: bool
    reason: str
    estimated_cost_usd: float = 0.0
    key_fingerprint: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "estimated_cost_usd": self.estimated_cost_usd,
            "key_fingerprint": self.key_fingerprint,
        }


def _period() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(Decimal(str(value)))
    except (ValueError, InvalidOperation, TypeError):
        return None


def _tokens(usage: Optional[Dict[str, Any]]) -> tuple[int, int]:
    usage = usage or {}
    return (
        int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
    )


class ModelUsageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _prices(self, model: str) -> tuple[Optional[float], Optional[float]]:
        try:
            result = await self.db.execute(
                select(DiscoveredModel).where(DiscoveredModel.model_id == model)
            )
            row = result.scalar_one_or_none()
        except Exception:
            return None, None
        if not row:
            return None, None
        return (
            _to_float(getattr(row, "cost_input_per_1m", None)),
            _to_float(getattr(row, "cost_output_per_1m", None)),
        )

    async def _limit_for(self, key_fingerprint: Optional[str]) -> Optional[float]:
        if key_fingerprint:
            try:
                result = await self.db.execute(
                    select(ModelProviderKey).where(
                        ModelProviderKey.key_fingerprint == key_fingerprint
                    )
                )
                row = result.scalar_one_or_none()
                limit = _to_float(getattr(row, "monthly_limit_usd", None)) if row else None
                if limit is not None:
                    return limit
            except Exception:
                return None
        return _to_float(
            getattr(settings, "finance_monthly_limit_usd", None)
        )

    async def _spent(self, model: str) -> Optional[float]:
        try:
            result = await self.db.execute(
                select(ProviderUsage).where(
                    ProviderUsage.model_id == model,
                    ProviderUsage.period == _period(),
                )
            )
            total = 0.0
            for row in result.scalars().all():
                amount = _to_float(getattr(row, "estimated_cost_usd", 0))
                if amount is None:
                    return None
                total += amount
            return total
        except Exception:
            return None

    async def preflight(
        self,
        *,
        model: str,
        is_paid: bool,
        authorization: Optional[Dict[str, Any]] = None,
        key_fingerprint: Optional[str] = None,
        estimated_input_tokens: int = 1000,
        estimated_output_tokens: int = 1000,
    ) -> UsageDecision:
        """Decide whether a request may reach a provider. Never fails open."""
        if not is_paid:
            return UsageDecision(True, "free or local inference; no spend authorisation needed")
        if not authorization or not authorization.get("authorized"):
            return UsageDecision(False, "no active signed authorisation for paid inference")
        in_price, out_price = await self._prices(model)
        if in_price is None or out_price is None:
            return UsageDecision(False, "applicable cost cannot be determined for this model")
        limit = await self._limit_for(key_fingerprint)
        if limit is None or limit <= 0:
            return UsageDecision(False, "no positive spending limit is configured")
        spent = await self._spent(model)
        if spent is None:
            return UsageDecision(False, "current spend cannot be determined")
        estimate = (
            estimated_input_tokens * in_price + estimated_output_tokens * out_price
        ) / 1_000_000
        if spent + estimate > limit:
            return UsageDecision(False, "request would exceed the remaining budget")
        return UsageDecision(
            True,
            "authorised, budgeted and costed",
            estimated_cost_usd=estimate,
            key_fingerprint=key_fingerprint,
        )

    async def record(
        self,
        *,
        model: str,
        provider: str,
        usage: Optional[Dict[str, Any]],
        is_paid: bool,
        decision: Optional[UsageDecision] = None,
        key_fingerprint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Persist token/cost accounting with model and key attribution."""
        tokens_in, tokens_out = _tokens(usage)
        in_price, out_price = await self._prices(model)
        cost = 0.0
        cost_determined = True
        if in_price is None or out_price is None:
            cost_determined = False
        else:
            cost = (tokens_in * in_price + tokens_out * out_price) / 1_000_000
        fingerprint = key_fingerprint or (decision.key_fingerprint if decision else None)

        provider_id = None
        try:
            result = await self.db.execute(
                select(AIProvider).where(AIProvider.name == provider)
            )
            provider_row = cast(Any, result.scalar_one_or_none())
            provider_id = provider_row.id if provider_row else None
        except Exception:
            provider_id = None

        # A deterministic id keeps spend accounting intact even when the
        # provider catalog row has not been initialised yet.
        if provider_id is None:
            provider_id = uuid5(NAMESPACE_URL, f"iam:provider:{provider}")
        self.db.add(
            ProviderUsage(
                provider_id=provider_id,
                model_id=model,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                estimated_cost_usd=cost,
                period=_period(),
            )
        )
        self.db.add(
            RequestUsage(
                session_id=None,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                provider=provider,
                model=model,
                cost_usd=cost,
            )
        )
        await self.db.flush()
        await self.db.commit()
        return {
            "model": model,
            "provider": provider,
            "key_fingerprint": fingerprint,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "cost_usd": cost,
            "cost_determined": cost_determined,
            "is_paid": is_paid,
            "authorised": bool(decision and decision.allowed) if is_paid else True,
        }
