"""Doc 25 Amendment A APIs — prediction, gaming and investment research.

Every endpoint is research-only. There is no endpoint for placing a wager,
funding a casino account, enabling prediction-market execution or placing a
real investment order.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.financial_intelligence.policy import IntelligenceDenied
from app.services.financial_intelligence.provider_registry import ProviderRegistryService
from app.services.gaming_intelligence.service import GamingDenied, GamingIntelligenceService
from app.services.investment_intelligence.service import InvestmentDenied, InvestmentIntelligenceService
from app.services.prediction_markets.adapter import PolymarketDataAdapter
from app.services.prediction_markets.forecasting import ForecastDenied, ForecastEngine
from app.services.prediction_markets.service import PredictionMarketDenied, PredictionMarketService

prediction_markets_router = APIRouter(
    prefix="/api/v1/prediction-markets", tags=["prediction-markets"]
)
gaming_intelligence_router = APIRouter(
    prefix="/api/v1/gaming-intelligence", tags=["gaming-intelligence"]
)
investment_intelligence_router = APIRouter(
    prefix="/api/v1/investment-intelligence", tags=["investment-intelligence"]
)
provider_registry_router = APIRouter(
    prefix="/api/v1/provider-registry", tags=["provider-registry"]
)


class MarketCreate(BaseModel):
    platform: str
    market_ref: str
    event_name: str
    outcomes: List[str]
    implied_probabilities: Dict[str, float]
    source_url: Optional[str] = None


class EstimateCreate(BaseModel):
    outcome: str
    iam_probability: float
    evidence: List[str] = Field(default_factory=list)


class LegalClearanceCreate(BaseModel):
    approval_id: str


class AdapterSyncCreate(BaseModel):
    limit: Optional[int] = None


class OrderBookCreate(BaseModel):
    token_id: str


class DataQueryCreate(BaseModel):
    path: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ForecastEvidence(BaseModel):
    outcome: str
    strength: float = Field(ge=0, le=1)
    source: str
    description: str = ""


class ForecastRunCreate(BaseModel):
    market_id: str
    method: str = "evidence_weighted"
    evidence: List[ForecastEvidence] = Field(default_factory=list)
    priors: Dict[str, float] = Field(default_factory=dict)
    rationale: str


class GamingAnalysisCreate(BaseModel):
    game: str
    rtp: float
    house_edge: float
    methodology: str
    sample_size: int = 0
    provider: Optional[str] = None
    findings: Dict[str, Any] = Field(default_factory=dict)


class RtpScenarioCreate(BaseModel):
    rtp: float
    wager: float
    plays: int


class ThesisCreate(BaseModel):
    asset_class: str
    symbol: str
    thesis: str
    risk_notes: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)


class RebalanceCreate(BaseModel):
    portfolio_ref: str
    allocations: Dict[str, float]
    rationale: str


class ProviderCreate(BaseModel):
    name: str
    category: str
    access_model: str = "free"
    documented_api_and_auth: bool = False
    commercial_use: bool = False
    automated_use: bool = False
    south_africa_supported: bool = False
    sandbox_available: bool = False
    licence_required: bool = False
    licence_requirements_recorded: bool = False
    gates_reviewed: bool = False
    notes: Optional[str] = None


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "iam") if credential else "iam"


def _denied(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(404, str(exc))
    if isinstance(exc, (IntelligenceDenied, ValueError)):
        return HTTPException(403 if isinstance(exc, IntelligenceDenied) else 400, str(exc))
    raise exc


# --- Prediction markets -------------------------------------------------------

@prediction_markets_router.get("/policy")
async def prediction_policy(db: AsyncSession = Depends(get_db_session)):
    return PredictionMarketService(db).policy()


@prediction_markets_router.get("/execution-adapter")
async def prediction_execution_adapter():
    return PredictionMarketService.execution_adapter()


@prediction_markets_router.get("/adapter/policy")
async def prediction_adapter_policy(db: AsyncSession = Depends(get_db_session)):
    return PolymarketDataAdapter(db).policy()


@prediction_markets_router.get("/adapter/status")
async def prediction_adapter_status(db: AsyncSession = Depends(get_db_session)):
    return PolymarketDataAdapter(db).status()


@prediction_markets_router.post("/adapter/sync")
async def sync_prediction_markets(
    payload: AdapterSyncCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Fetch public Gamma markets; records implied probabilities only."""
    try:
        return await PolymarketDataAdapter(db).sync_markets(_actor(request), payload.limit)
    except (PredictionMarketDenied, LookupError, ValueError) as exc:
        raise _denied(exc) from exc


@prediction_markets_router.post("/adapter/order-book")
async def prediction_order_book(
    payload: OrderBookCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Read-only CLOB snapshot — no order is placed."""
    try:
        return await PolymarketDataAdapter(db).fetch_order_book(payload.token_id)
    except (PredictionMarketDenied, ValueError) as exc:
        raise _denied(exc) from exc


@prediction_markets_router.post("/adapter/data")
async def prediction_data_query(
    payload: DataQueryCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Read-only GET against the configured public Data API base URL."""
    try:
        return await PolymarketDataAdapter(db).fetch_data(payload.path, payload.params)
    except (PredictionMarketDenied, ValueError) as exc:
        raise _denied(exc) from exc


@prediction_markets_router.get("/forecast/policy")
async def forecast_policy(db: AsyncSession = Depends(get_db_session)):
    return ForecastEngine(db).policy()


@prediction_markets_router.post("/forecast/run")
async def run_forecast(
    payload: ForecastRunCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Record IAM's independent probability estimates for a market."""
    try:
        return await ForecastEngine(db).run(
            market_id=payload.market_id,
            method=payload.method,
            evidence=[item.model_dump() for item in payload.evidence],
            priors=payload.priors,
            rationale=payload.rationale,
            actor=_actor(request),
        )
    except (ForecastDenied, PredictionMarketDenied, LookupError, ValueError) as exc:
        raise _denied(exc) from exc


@prediction_markets_router.get("/forecast/runs/{market_id}")
async def list_forecast_runs(market_id: str, db: AsyncSession = Depends(get_db_session)):
    try:
        return await ForecastEngine(db).runs(market_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@prediction_markets_router.post("/markets")
async def register_market(
    payload: MarketCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PredictionMarketService(db).register_market(
            platform=payload.platform,
            market_ref=payload.market_ref,
            event_name=payload.event_name,
            outcomes=payload.outcomes,
            implied_probabilities=payload.implied_probabilities,
            source_url=payload.source_url,
            actor=_actor(request),
        )
    except (PredictionMarketDenied, LookupError, ValueError) as exc:
        raise _denied(exc) from exc


@prediction_markets_router.get("/markets")
async def list_markets(db: AsyncSession = Depends(get_db_session)):
    return await PredictionMarketService(db).markets()


@prediction_markets_router.get("/markets/{market_id}/comparison")
async def compare_market(market_id: str, db: AsyncSession = Depends(get_db_session)):
    try:
        return await PredictionMarketService(db).compare(market_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@prediction_markets_router.post("/markets/{market_id}/estimates")
async def record_estimate(
    market_id: str,
    payload: EstimateCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PredictionMarketService(db).record_estimate(
            market_id=market_id,
            outcome=payload.outcome,
            iam_probability=payload.iam_probability,
            evidence=payload.evidence,
            actor=_actor(request),
        )
    except (PredictionMarketDenied, LookupError, ValueError) as exc:
        raise _denied(exc) from exc


@prediction_markets_router.get("/markets/{market_id}/estimates")
async def list_estimates(market_id: str, db: AsyncSession = Depends(get_db_session)):
    try:
        return await PredictionMarketService(db).estimates(market_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@prediction_markets_router.post("/markets/{market_id}/legal-clearance")
async def record_legal_clearance(
    market_id: str,
    payload: LegalClearanceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PredictionMarketService(db).request_legal_clearance(
            market_id, payload.approval_id, _actor(request)
        )
    except (PredictionMarketDenied, LookupError, ValueError) as exc:
        raise _denied(exc) from exc


# --- Gaming intelligence -----------------------------------------------------

@gaming_intelligence_router.get("/policy")
async def gaming_policy(db: AsyncSession = Depends(get_db_session)):
    return GamingIntelligenceService(db).policy()


@gaming_intelligence_router.get("/records")
async def list_gaming_records(db: AsyncSession = Depends(get_db_session)):
    return await GamingIntelligenceService(db).records()


@gaming_intelligence_router.get("/records/{record_id}")
async def get_gaming_record(record_id: str, db: AsyncSession = Depends(get_db_session)):
    try:
        return await GamingIntelligenceService(db).record_by_id(record_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@gaming_intelligence_router.post("/records")
async def record_gaming_analysis(
    payload: GamingAnalysisCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await GamingIntelligenceService(db).record_analysis(
            game=payload.game,
            rtp=payload.rtp,
            house_edge=payload.house_edge,
            methodology=payload.methodology,
            sample_size=payload.sample_size,
            provider=payload.provider,
            findings=payload.findings,
            actor=_actor(request),
        )
    except (GamingDenied, ValueError) as exc:
        raise _denied(exc) from exc


@gaming_intelligence_router.post("/rtp-scenario")
async def rtp_scenario(payload: RtpScenarioCreate, db: AsyncSession = Depends(get_db_session)):
    try:
        return GamingIntelligenceService(db).rtp_scenario(
            payload.rtp, payload.wager, payload.plays
        )
    except (GamingDenied, ValueError) as exc:
        raise _denied(exc) from exc


# --- Investment intelligence -------------------------------------------------

@investment_intelligence_router.get("/policy")
async def investment_policy(db: AsyncSession = Depends(get_db_session)):
    return InvestmentIntelligenceService(db).policy()


@investment_intelligence_router.get("/records")
async def list_investment_records(db: AsyncSession = Depends(get_db_session)):
    return await InvestmentIntelligenceService(db).records()


@investment_intelligence_router.get("/records/{record_id}")
async def get_investment_record(record_id: str, db: AsyncSession = Depends(get_db_session)):
    try:
        return await InvestmentIntelligenceService(db).record_by_id(record_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@investment_intelligence_router.post("/records")
async def record_thesis(
    payload: ThesisCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await InvestmentIntelligenceService(db).record_thesis(
            asset_class=payload.asset_class,
            symbol=payload.symbol,
            thesis=payload.thesis,
            risk_notes=payload.risk_notes,
            evidence=payload.evidence,
            actor=_actor(request),
        )
    except (InvestmentDenied, ValueError) as exc:
        raise _denied(exc) from exc


@investment_intelligence_router.post("/rebalance-proposals")
async def record_rebalance(
    payload: RebalanceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await InvestmentIntelligenceService(db).record_rebalance_proposal(
            portfolio_ref=payload.portfolio_ref,
            allocations=payload.allocations,
            rationale=payload.rationale,
            actor=_actor(request),
        )
    except (InvestmentDenied, ValueError) as exc:
        raise _denied(exc) from exc


# --- Provider registry -------------------------------------------------------

@provider_registry_router.get("/policy")
async def provider_policy(db: AsyncSession = Depends(get_db_session)):
    return ProviderRegistryService(db).policy()


@provider_registry_router.post("/seed")
async def seed_providers(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """Record §18 candidates locally. No network call or adapter enablement."""
    try:
        return await ProviderRegistryService(db).seed_candidates(_actor(request))
    except (IntelligenceDenied, ValueError) as exc:
        raise _denied(exc) from exc


@provider_registry_router.get("/entries")
async def list_providers(db: AsyncSession = Depends(get_db_session)):
    return await ProviderRegistryService(db).entries()


@provider_registry_router.post("/entries")
async def register_provider(
    payload: ProviderCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ProviderRegistryService(db).register(
            name=payload.name,
            category=payload.category,
            access_model=payload.access_model,
            documented_api_and_auth=payload.documented_api_and_auth,
            commercial_use=payload.commercial_use,
            automated_use=payload.automated_use,
            south_africa_supported=payload.south_africa_supported,
            sandbox_available=payload.sandbox_available,
            licence_required=payload.licence_required,
            licence_requirements_recorded=payload.licence_requirements_recorded,
            gates_reviewed=payload.gates_reviewed,
            notes=payload.notes,
            actor=_actor(request),
        )
    except (IntelligenceDenied, LookupError, ValueError) as exc:
        raise _denied(exc) from exc


@provider_registry_router.get("/entries/{name}/evaluation")
async def evaluate_provider(name: str, db: AsyncSession = Depends(get_db_session)):
    try:
        return await ProviderRegistryService(db).evaluate(name)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@provider_registry_router.post("/entries/{name}/enable")
async def enable_provider(
    name: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await ProviderRegistryService(db).enable_adapter(name, _actor(request))
    except (IntelligenceDenied, LookupError, ValueError) as exc:
        raise _denied(exc) from exc
