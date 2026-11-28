"""Prediction market research — public data, independent probabilities, no execution.

This service discovers event contracts, records IAM's own probability estimates
and compares them with market-implied probabilities. The execution adapter is
permanently disabled in this implementation; legal clearance only records review,
it never opens a trading or wallet-funding path.
"""

from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.financial_intelligence import PredictionMarket, ProbabilityEstimate
from app.models.security import AuditEvent
from app.services.creatorapproval_service import CreatorApprovalService
from app.services.financial_intelligence.policy import (
    LEGAL_CLEARANCE_ACTION,
    LEGAL_CLEARANCE_LEVEL,
    PREDICTION_PLATFORMS,
    RESEARCH_DISCLAIMER,
    SOUTH_AFRICA_NOTICE,
    IntelligenceDenied,
)


class PredictionMarketDenied(IntelligenceDenied):
    """Raised when a prediction-market action breaks a research-only boundary."""


class PredictionMarketService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "research_enabled": settings.prediction_markets_research_enabled,
            "research_only": True,
            "public_market_data_only": True,
            "execution_adapter_enabled": False,
            "real_money_enabled": False,
            "legal_clearance_action": LEGAL_CLEARANCE_ACTION,
            "platforms": list(PREDICTION_PLATFORMS),
            "disclaimer": RESEARCH_DISCLAIMER,
            "south_africa_notice": SOUTH_AFRICA_NOTICE,
        }

    @staticmethod
    def execution_adapter() -> Dict[str, Any]:
        return {
            "enabled": False,
            "reason": "execution requires separate legal clearance and explicit authorisation",
        }

    async def execute(self, *args: Any, **kwargs: Any) -> None:
        """There is no execution path. Kept explicit so it cannot be added silently."""
        raise PredictionMarketDenied("prediction-market execution adapter is disabled")

    async def register_market(
        self,
        *,
        platform: str,
        market_ref: str,
        event_name: str,
        outcomes: Sequence[str],
        implied_probabilities: Dict[str, float],
        source_url: Optional[str] = None,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        if not settings.prediction_markets_research_enabled:
            raise PredictionMarketDenied("prediction-market research is disabled")
        if platform not in PREDICTION_PLATFORMS:
            raise PredictionMarketDenied("unsupported prediction platform")
        if not market_ref or not event_name:
            raise PredictionMarketDenied("market_ref and event_name are required")
        outcomes = list(outcomes)
        if not outcomes or len(set(outcomes)) != len(outcomes):
            raise PredictionMarketDenied("outcomes must be a non-empty list of unique values")
        for outcome in outcomes:
            probability = implied_probabilities.get(outcome)
            if not isinstance(probability, (int, float)) or not 0 <= float(probability) <= 1:
                raise PredictionMarketDenied(
                    "each outcome needs an implied probability between 0 and 1"
                )

        result = await self.db.execute(select(PredictionMarket))
        for row in result.scalars().all():
            if row.platform == platform and row.market_ref == market_ref:
                raise PredictionMarketDenied("market already registered")

        market = PredictionMarket(
            platform=platform,
            market_ref=market_ref,
            event_name=event_name,
            outcomes=outcomes,
            implied_probabilities=dict(implied_probabilities),
            source_url=source_url,
            legal_status="research_only",
            real_money_enabled=False,
        )
        self.db.add(market)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="prediction_market_discovered",
                actor=actor,
                target=str(market.id),
                details={
                    "platform": platform,
                    "market_ref": market_ref,
                    "outcomes": outcomes,
                    "research_only": True,
                },
            )
        )
        await self.db.commit()
        return self._market(market)

    async def record_estimate(
        self,
        *,
        market_id: str,
        outcome: str,
        iam_probability: float,
        evidence: Optional[Sequence[str]] = None,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        if not settings.prediction_markets_research_enabled:
            raise PredictionMarketDenied("prediction-market research is disabled")
        market = await self._market_by_id(market_id)
        if outcome not in (market.outcomes or []):
            raise PredictionMarketDenied("outcome is not part of this market")
        try:
            value = float(iam_probability)
        except (TypeError, ValueError) as exc:
            raise PredictionMarketDenied("iam_probability must be numeric") from exc
        if not 0 <= value <= 1:
            raise PredictionMarketDenied("iam_probability must be between 0 and 1")

        estimate = ProbabilityEstimate(
            market_id=market.id,
            outcome=outcome,
            iam_probability=value,
            evidence=list(evidence or []),
            analyst=actor,
        )
        self.db.add(estimate)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="prediction_probability_recorded",
                actor=actor,
                target=str(estimate.id),
                details={
                    "market_id": str(market.id),
                    "outcome": outcome,
                    "iam_probability": value,
                },
            )
        )
        await self.db.commit()
        return self._estimate(estimate)

    async def compare(self, market_id: str) -> Dict[str, Any]:
        market = await self._market_by_id(market_id)
        estimates = await self._estimates(market.id)  # type: ignore[arg-type]
        comparisons = []
        implied: Any = market.implied_probabilities or {}
        for estimate in estimates:
            market_probability = float(implied.get(estimate.outcome, 0) or 0)
            iam_probability = float(estimate.iam_probability)
            comparisons.append(
                {
                    "outcome": estimate.outcome,
                    "market_probability": market_probability,
                    "iam_probability": iam_probability,
                    "difference_percentage_points": round(
                        (iam_probability - market_probability) * 100, 2
                    ),
                    "evidence": estimate.evidence or [],
                }
            )
        return {
            "market": self._market(market),
            "comparisons": comparisons,
            "not_profitable_by_itself": True,
            "disclaimer": RESEARCH_DISCLAIMER,
            "south_africa_notice": SOUTH_AFRICA_NOTICE,
            "execution_adapter_enabled": False,
        }

    async def request_legal_clearance(
        self, market_id: str, approval_id: Optional[str], actor: str = "iam"
    ) -> Dict[str, Any]:
        """Record legal review only. This never enables real-money participation."""
        market = await self._market_by_id(market_id)
        if not approval_id:
            raise PredictionMarketDenied("legal clearance requires a signed Creator approval_id")
        authority = await CreatorApprovalService(self.db).check_authorization(
            LEGAL_CLEARANCE_ACTION, requested_level=LEGAL_CLEARANCE_LEVEL, target_ref=str(approval_id)
        )
        if not authority.get("authorized"):
            raise PredictionMarketDenied("no active signed Creator authorization for legal clearance")
        market.legal_status = "cleared"  # type: ignore[assignment]
        market.real_money_enabled = False  # type: ignore[assignment]
        self.db.add(
            AuditEvent(
                event_type="prediction_market_legal_clearance_recorded",
                actor=actor,
                target=str(market.id),
                details={
                    "authorization_id": authority["authorization_id"],
                    "execution_still_disabled": True,
                },
            )
        )
        await self.db.commit()
        return {
            **self._market(market),
            "authorization_id": authority["authorization_id"],
            "execution_still_disabled": True,
        }

    async def get_market(self, market_id: str) -> Dict[str, Any]:
        return self._market(await self._market_by_id(market_id))

    async def markets(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(PredictionMarket))
        return [self._market(row) for row in result.scalars().all()]

    async def estimates(self, market_id: str) -> List[Dict[str, Any]]:
        market = await self._market_by_id(market_id)
        return [self._estimate(row) for row in await self._estimates(market.id)]  # type: ignore[arg-type]

    async def _market_by_id(self, market_id: str) -> PredictionMarket:
        try:
            identifier = UUID(str(market_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise LookupError("market not found") from exc
        result = await self.db.execute(
            select(PredictionMarket).where(PredictionMarket.id == identifier)
        )
        market = result.scalar_one_or_none()
        if not market:
            raise LookupError("market not found")
        return market

    async def _estimates(self, market_id: UUID) -> List[ProbabilityEstimate]:
        result = await self.db.execute(
            select(ProbabilityEstimate).where(ProbabilityEstimate.market_id == market_id)
        )
        return list(result.scalars().all())

    @staticmethod
    def _market(market: PredictionMarket) -> Dict[str, Any]:
        return {
            "id": str(market.id),
            "platform": market.platform,
            "market_ref": market.market_ref,
            "event_name": market.event_name,
            "outcomes": market.outcomes or [],
            "implied_probabilities": market.implied_probabilities or {},
            "legal_status": market.legal_status,
            "real_money_enabled": bool(market.real_money_enabled),
            "research_only": True,
        }

    @staticmethod
    def _estimate(estimate: ProbabilityEstimate) -> Dict[str, Any]:
        return {
            "id": str(estimate.id),
            "market_id": str(estimate.market_id),
            "outcome": estimate.outcome,
            "iam_probability": float(estimate.iam_probability),
            "evidence": estimate.evidence or [],
        }
