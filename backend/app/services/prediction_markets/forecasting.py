"""Independent probability forecasting for prediction markets.

IAM estimates probabilities from its own research evidence. Market-implied
probabilities are never an input: they are only read afterwards for comparison.
Every run records its method, inputs, evidence and formula so the estimate is
auditable rather than a black-box assertion.
"""

from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.financial_intelligence import ForecastRun
from app.models.security import AuditEvent
from app.services.financial_intelligence.policy import RESEARCH_DISCLAIMER
from app.services.prediction_markets.service import (
    PredictionMarketDenied,
    PredictionMarketService,
)

METHODS = ("evidence_weighted", "base_rate")

FORMULAS = {
    "evidence_weighted": (
        "score(outcome) = prior(outcome) + sum(evidence strength for outcome); "
        "probability(outcome) = score / total score"
    ),
    "base_rate": (
        "score(outcome) = researched base rate (or prior) for outcome; "
        "probability(outcome) = score / total score"
    ),
}


class ForecastDenied(PredictionMarketDenied):
    """Raised when a forecast has invalid evidence or crosses a policy boundary."""


class ForecastEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.prediction_markets_forecasting_enabled,
            "methods": list(METHODS),
            "formulas": dict(FORMULAS),
            "independent_of_market_prices": True,
            "market_implied_probabilities_used": False,
            "evidence_required": True,
            "disclaimer": RESEARCH_DISCLAIMER,
        }

    @staticmethod
    def compute(
        method: str,
        outcomes: Sequence[str],
        evidence: Sequence[Dict[str, Any]],
        priors: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Pure, deterministic probability calculation from research evidence."""
        if method not in METHODS:
            raise ForecastDenied(f"unknown forecast method: {method}")
        outcomes = list(outcomes)
        if not outcomes or len(set(outcomes)) != len(outcomes):
            raise ForecastDenied("outcomes must be a non-empty list of unique values")
        evidence = list(evidence or [])
        if not evidence:
            raise ForecastDenied("a forecast requires research evidence")

        scores = {outcome: 0.0 for outcome in outcomes}
        for outcome, value in (priors or {}).items():
            if outcome not in scores:
                raise ForecastDenied(f"prior references unknown outcome: {outcome}")
            try:
                prior = float(value)
            except (TypeError, ValueError) as exc:
                raise ForecastDenied("priors must be numeric") from exc
            if prior < 0:
                raise ForecastDenied("priors must be non-negative")
            scores[outcome] += prior

        normalised_evidence: List[Dict[str, Any]] = []
        for item in evidence:
            if not isinstance(item, dict):
                raise ForecastDenied("evidence items must be objects")
            outcome = item.get("outcome")  # type: ignore[assignment]
            if outcome not in scores:
                raise ForecastDenied(f"evidence references unknown outcome: {outcome}")
            source = str(item.get("source") or "").strip()
            if not source:
                raise ForecastDenied("each evidence item requires a source")
            try:
                strength = float(item.get("strength"))  # type: ignore[arg-type]
            except (TypeError, ValueError) as exc:
                raise ForecastDenied("evidence strength must be numeric") from exc
            if not 0 <= strength <= 1:
                raise ForecastDenied("evidence strength must be between 0 and 1")
            normalised_evidence.append(
                {
                    "outcome": outcome,
                    "strength": strength,
                    "source": source,
                    "description": str(item.get("description") or ""),
                }
            )
            if method == "evidence_weighted":
                scores[outcome] += strength
            else:
                scores[outcome] = max(scores[outcome], strength)

        total = sum(scores.values())
        if total <= 0:
            raise ForecastDenied("evidence and priors must give a positive total score")

        probabilities = {
            outcome: round(score / total, 6) for outcome, score in scores.items()
        }
        last = outcomes[-1]
        probabilities[last] = round(probabilities[last] + (1.0 - sum(probabilities.values())), 6)

        return {
            "method": method,
            "probabilities": probabilities,
            "scores": {key: round(value, 6) for key, value in scores.items()},
            "confidence": round(min(1.0, total), 6),
            "evidence_count": len(normalised_evidence),
            "evidence": normalised_evidence,
            "formula": FORMULAS[method],
            "market_implied_probabilities_used": False,
        }

    async def run(
        self,
        *,
        market_id: str,
        method: str,
        evidence: Sequence[Dict[str, Any]],
        rationale: str,
        priors: Optional[Dict[str, float]] = None,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        if not settings.prediction_markets_forecasting_enabled:
            raise ForecastDenied("independent forecasting is disabled")
        if not settings.prediction_markets_research_enabled:
            raise ForecastDenied("prediction-market research is disabled")
        if not rationale or not str(rationale).strip():
            raise ForecastDenied("a forecast requires a documented rationale")

        service = PredictionMarketService(self.db)
        market = await service.get_market(market_id)
        result = self.compute(method, market["outcomes"], evidence, priors)

        run = ForecastRun(
            market_id=UUID(str(market["id"])),
            method=method,
            inputs={
                "method": method,
                "priors": dict(priors or {}),
                "outcomes": market["outcomes"],
            },
            probabilities=result["probabilities"],
            evidence=result["evidence"],
            rationale=str(rationale),
            confidence=result["confidence"],
            market_implied_probabilities_used=False,
        )
        self.db.add(run)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="prediction_forecast_recorded",
                actor=actor,
                target=str(run.id),
                details={
                    "market_id": market["id"],
                    "method": method,
                    "confidence": result["confidence"],
                    "market_implied_probabilities_used": False,
                },
            )
        )

        estimates = []
        for outcome, probability in result["probabilities"].items():
            supporting = [
                f"{item['source']}: {item['description']} (strength {item['strength']})"
                for item in result["evidence"]
                if item["outcome"] == outcome
            ]
            estimates.append(
                await service.record_estimate(
                    market_id=market["id"],
                    outcome=outcome,
                    iam_probability=probability,
                    evidence=supporting,
                    actor=actor,
                )
            )

        await self.db.commit()
        comparison = await service.compare(market["id"])
        return {
            "run": self._run(run),
            "method": result["method"],
            "formula": result["formula"],
            "confidence": result["confidence"],
            "estimates": estimates,
            "comparison": comparison,
            "independent": True,
            "market_implied_probabilities_used": False,
        }

    async def runs(self, market_id: str) -> List[Dict[str, Any]]:
        service = PredictionMarketService(self.db)
        market = await service.get_market(market_id)
        result = await self.db.execute(
            select(ForecastRun).where(ForecastRun.market_id == market["id"])
        )
        return [self._run(row) for row in result.scalars().all()]

    @staticmethod
    def _run(run: ForecastRun) -> Dict[str, Any]:
        return {
            "id": str(run.id),
            "market_id": str(run.market_id),
            "method": run.method,
            "inputs": run.inputs or {},
            "probabilities": run.probabilities or {},
            "evidence": run.evidence or [],
            "rationale": run.rationale,
            "confidence": float(run.confidence),
            "market_implied_probabilities_used": bool(run.market_implied_probabilities_used),
        }
