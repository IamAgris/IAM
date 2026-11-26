"""Stocks, ETFs, commodities, bonds and portfolio research — no order execution."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.financial_intelligence import InvestmentResearchRecord
from app.models.security import AuditEvent
from app.services.financial_intelligence.policy import (
    ASSET_CLASSES,
    IntelligenceDenied,
)


class InvestmentDenied(IntelligenceDenied):
    """Raised when an investment action crosses into real execution."""


class InvestmentIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.investment_intelligence_research_enabled,
            "research_only": True,
            "order_execution_enabled": False,
            "asset_classes": list(ASSET_CLASSES),
            "no_profit_guarantees": True,
        }

    async def place_order(self, *args: Any, **kwargs: Any) -> None:
        raise InvestmentDenied("investment research cannot place real orders")

    async def record_thesis(
        self,
        *,
        asset_class: str,
        symbol: str,
        thesis: str,
        risk_notes: Optional[str] = None,
        evidence: Optional[Dict[str, Any]] = None,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        if not settings.investment_intelligence_research_enabled:
            raise InvestmentDenied("investment research is disabled")
        if asset_class not in ASSET_CLASSES or not symbol or not thesis:
            raise InvestmentDenied("known asset_class, symbol and thesis are required")

        record = InvestmentResearchRecord(
            asset_class=asset_class,
            symbol=symbol,
            thesis=thesis,
            risk_notes=risk_notes,
            evidence=dict(evidence or {}),
            execution_enabled=False,
        )
        self.db.add(record)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="investment_thesis_recorded",
                actor=actor,
                target=str(record.id),
                details={
                    "asset_class": asset_class,
                    "symbol": symbol,
                    "execution_enabled": False,
                },
            )
        )
        await self.db.commit()
        return self._record(record)

    async def record_rebalance_proposal(
        self,
        *,
        portfolio_ref: str,
        allocations: Dict[str, float],
        rationale: str,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        """Record a portfolio proposal only — never submit it to a broker."""
        if not settings.investment_intelligence_research_enabled:
            raise InvestmentDenied("investment research is disabled")
        if not portfolio_ref or not allocations or not rationale:
            raise InvestmentDenied("portfolio_ref, allocations and rationale are required")
        try:
            total = sum(float(value) for value in allocations.values())
        except (TypeError, ValueError) as exc:
            raise InvestmentDenied("allocations must be numeric") from exc
        if abs(total - 1.0) > 0.0001:
            raise InvestmentDenied("allocations must sum to 1")

        return await self.record_thesis(
            asset_class="portfolio",
            symbol=portfolio_ref,
            thesis=rationale,
            risk_notes="Portfolio proposal recorded for research; no order was placed.",
            evidence={"allocations": dict(allocations), "proposal_only": True},
            actor=actor,
        )

    async def records(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(InvestmentResearchRecord))
        return [self._record(row) for row in result.scalars().all()]

    async def record_by_id(self, record_id: str) -> Dict[str, Any]:
        try:
            identifier = UUID(str(record_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise LookupError("record not found") from exc
        result = await self.db.execute(
            select(InvestmentResearchRecord).where(InvestmentResearchRecord.id == identifier)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise LookupError("record not found")
        return self._record(record)

    @staticmethod
    def _record(record: InvestmentResearchRecord) -> Dict[str, Any]:
        return {
            "id": str(record.id),
            "asset_class": record.asset_class,
            "symbol": record.symbol,
            "thesis": record.thesis,
            "risk_notes": record.risk_notes,
            "evidence": record.evidence or {},
            "execution_enabled": False,
        }
