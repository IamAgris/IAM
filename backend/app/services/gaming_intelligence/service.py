"""Casino game mathematics and RNG research — no wagering or account funding.

Return-to-player figures are long-run statistical measures, not a promised
return on an individual session. Outcomes from a properly implemented RNG are
independent and cannot be predicted from previous results.
"""

from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.financial_intelligence import GamingResearchRecord
from app.models.security import AuditEvent
from app.services.financial_intelligence.policy import IntelligenceDenied

RTP_DISCLAIMER = (
    "Illustrative long-run mathematics only; not a guaranteed outcome on any "
    "particular session. Past results cannot predict independent RNG outcomes."
)


class GamingDenied(IntelligenceDenied):
    """Raised when a gaming action crosses into wagering or account funding."""


class GamingIntelligenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.gaming_intelligence_enabled,
            "research_only": True,
            "wagering_enabled": False,
            "account_funding_enabled": False,
            "topics": (
                "probability_mathematics",
                "statistical_analysis",
                "game_theory",
                "rng_research",
                "rtp_analysis",
                "house_edge",
                "fraud_detection",
                "responsible_gambling",
            ),
            "disclaimer": RTP_DISCLAIMER,
        }

    async def wager(self, *args: Any, **kwargs: Any) -> None:
        raise GamingDenied("autonomous casino wagering is prohibited")

    async def fund_account(self, *args: Any, **kwargs: Any) -> None:
        raise GamingDenied("overseas casino account funding is prohibited")

    async def record_analysis(
        self,
        *,
        game: str,
        rtp: float,
        house_edge: float,
        methodology: str,
        sample_size: int = 0,
        provider: Optional[str] = None,
        findings: Optional[Dict[str, Any]] = None,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        if not settings.gaming_intelligence_enabled:
            raise GamingDenied("gaming intelligence research is disabled")
        if not game or not methodology:
            raise GamingDenied("game and methodology are required")
        try:
            rtp_value = float(rtp)
            edge_value = float(house_edge)
            size = int(sample_size or 0)
        except (TypeError, ValueError) as exc:
            raise GamingDenied("rtp, house_edge and sample_size must be numeric") from exc
        if not 0 <= rtp_value <= 1 or not 0 <= edge_value <= 1:
            raise GamingDenied("rtp and house_edge must be between 0 and 1")
        if size < 0:
            raise GamingDenied("sample_size must be non-negative")

        record = GamingResearchRecord(
            game=game,
            provider=provider,
            rtp=rtp_value,
            house_edge=edge_value,
            sample_size=size,
            methodology=methodology,
            findings=dict(findings or {}),
            wagering_enabled=False,
        )
        self.db.add(record)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="gaming_analysis_recorded",
                actor=actor,
                target=str(record.id),
                details={"game": game, "rtp": rtp_value, "research_only": True},
            )
        )
        await self.db.commit()
        return self._record(record)

    def rtp_scenario(self, rtp: float, wager: float, plays: int) -> Dict[str, Any]:
        """Long-run expected-value illustration, never a session prediction."""
        try:
            rtp_value = float(rtp)
            wager_value = float(wager)
            count = int(plays)
        except (TypeError, ValueError) as exc:
            raise GamingDenied("rtp, wager and plays must be numeric") from exc
        if not 0 <= rtp_value <= 1 or wager_value < 0 or count < 0:
            raise GamingDenied("rtp must be 0–1; wager and plays must be non-negative")
        total_wagered = round(wager_value * count, 4)
        expected_return = round(total_wagered * rtp_value, 4)
        return {
            "total_wagered": total_wagered,
            "theoretical_return": expected_return,
            "expected_loss": round(total_wagered - expected_return, 4),
            "research_only": True,
            "disclaimer": RTP_DISCLAIMER,
        }

    async def records(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(GamingResearchRecord))
        return [self._record(row) for row in result.scalars().all()]

    async def record_by_id(self, record_id: str) -> Dict[str, Any]:
        try:
            identifier = UUID(str(record_id))
        except (ValueError, AttributeError, TypeError) as exc:
            raise LookupError("record not found") from exc
        result = await self.db.execute(
            select(GamingResearchRecord).where(GamingResearchRecord.id == identifier)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise LookupError("record not found")
        return self._record(record)

    @staticmethod
    def _record(record: GamingResearchRecord) -> Dict[str, Any]:
        return {
            "id": str(record.id),
            "game": record.game,
            "provider": record.provider,
            "rtp": float(record.rtp),
            "house_edge": float(record.house_edge),
            "sample_size": int(record.sample_size),
            "methodology": record.methodology,
            "findings": record.findings or {},
            "wagering_enabled": False,
        }
