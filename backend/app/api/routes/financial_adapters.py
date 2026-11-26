"""Free-only blockchain, consent-gated banking and paper-trading APIs."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.banking.service import BankingDenied, BankingService, BANKING_CAPABILITIES
from app.services.blockchain.service import BlockchainDenied, BlockchainService
from app.services.trading.paper import PaperTradingService, TradingDenied

blockchain_router = APIRouter(prefix="/api/v1/blockchain", tags=["blockchain"])
banking_router = APIRouter(prefix="/api/v1/banking", tags=["banking"])
trading_router = APIRouter(prefix="/api/v1/trading", tags=["trading"])


class ActivityCreate(BaseModel):
    asset: str
    amount: float
    address: str
    tx_hash: str = ""
    approval_id: Optional[str] = None


class ConsentCreate(BaseModel):
    institution: str
    account_ref: str
    capabilities: List[str] = Field(default_factory=list)
    approval_id: Optional[str] = None
    ttl_seconds: int = 3600


class PaymentCreate(BaseModel):
    consent_id: str
    amount: float
    beneficiary: str
    approval_id: Optional[str] = None


class PortfolioCreate(BaseModel):
    name: str
    starting_cash: float


class OrderCreate(BaseModel):
    symbol: str
    side: str
    quantity: float
    price: float


class LimitsUpdate(BaseModel):
    max_order_usd: Optional[float] = None
    daily_exposure_usd: Optional[float] = None
    max_loss_usd: Optional[float] = None
    stop_loss_pct: Optional[float] = None


class StopUpdate(BaseModel):
    enabled: bool


def _actor(request: Request) -> str:
    credential = getattr(request.state, "credential", None)
    return credential.get("name", "iam") if credential else "iam"


# --- Blockchain ---------------------------------------------------------------

@blockchain_router.get("/policy")
async def blockchain_policy(db: AsyncSession = Depends(get_db_session)):
    return BlockchainService(db).policy()


@blockchain_router.get("/status")
async def blockchain_status(db: AsyncSession = Depends(get_db_session)):
    return BlockchainService(db).status()


@blockchain_router.post("/activities")
async def record_activity(
    payload: ActivityCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await BlockchainService(db).record_activity(
            asset=payload.asset,
            amount=payload.amount,
            address=payload.address,
            tx_hash=payload.tx_hash,
            approval_id=payload.approval_id,
            actor=_actor(request),
        )
    except BlockchainDenied as exc:
        raise HTTPException(403, str(exc)) from exc


@blockchain_router.get("/activities")
async def list_activities(db: AsyncSession = Depends(get_db_session)):
    return await BlockchainService(db).activities()


# --- Banking ------------------------------------------------------------------

@banking_router.get("/policy")
async def banking_policy(db: AsyncSession = Depends(get_db_session)):
    return BankingService(db).policy()


@banking_router.get("/status")
async def banking_status(db: AsyncSession = Depends(get_db_session)):
    return BankingService(db).status()


@banking_router.get("/capabilities")
async def banking_capabilities():
    return {"capabilities": list(BANKING_CAPABILITIES)}


@banking_router.post("/consents")
async def request_consent(
    payload: ConsentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await BankingService(db).request_consent(
            institution=payload.institution,
            account_ref=payload.account_ref,
            capabilities=payload.capabilities,
            approval_id=payload.approval_id,
            ttl_seconds=payload.ttl_seconds,
            actor=_actor(request),
        )
    except BankingDenied as exc:
        raise HTTPException(403, str(exc)) from exc


@banking_router.get("/consents")
async def list_consents(db: AsyncSession = Depends(get_db_session)):
    return await BankingService(db).consents()


@banking_router.post("/consents/{consent_id}/revoke")
async def revoke_consent(
    consent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await BankingService(db).revoke_consent(consent_id, _actor(request))
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@banking_router.post("/payments")
async def propose_payment(
    payload: PaymentCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await BankingService(db).propose_payment(
            consent_id=payload.consent_id,
            amount=payload.amount,
            beneficiary=payload.beneficiary,
            approval_id=payload.approval_id,
            actor=_actor(request),
        )
    except BankingDenied as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, "invalid consent identifier") from exc


# --- Paper trading ------------------------------------------------------------

@trading_router.get("/policy")
async def trading_policy(db: AsyncSession = Depends(get_db_session)):
    return PaperTradingService(db).policy()


@trading_router.post("/portfolios")
async def create_portfolio(
    payload: PortfolioCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PaperTradingService(db).create_portfolio(
            payload.name, payload.starting_cash, _actor(request)
        )
    except TradingDenied as exc:
        raise HTTPException(403, str(exc)) from exc


@trading_router.get("/portfolios/{portfolio_id}")
async def portfolio_report(
    portfolio_id: str, db: AsyncSession = Depends(get_db_session)
):
    try:
        return await PaperTradingService(db).report(portfolio_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@trading_router.post("/portfolios/{portfolio_id}/orders")
async def place_order(
    portfolio_id: str,
    payload: OrderCreate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PaperTradingService(db).place_order(
            portfolio_id,
            symbol=payload.symbol,
            side=payload.side,
            quantity=payload.quantity,
            price=payload.price,
            actor=_actor(request),
        )
    except TradingDenied as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@trading_router.post("/portfolios/{portfolio_id}/limits")
async def set_limits(
    portfolio_id: str,
    payload: LimitsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PaperTradingService(db).set_limits(
            portfolio_id,
            payload.model_dump(exclude_none=True),
            _actor(request),
        )
    except TradingDenied as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@trading_router.post("/portfolios/{portfolio_id}/emergency-stop")
async def emergency_stop(
    portfolio_id: str,
    payload: StopUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    try:
        return await PaperTradingService(db).emergency_stop(
            portfolio_id, payload.enabled, _actor(request)
        )
    except TradingDenied as exc:
        raise HTTPException(403, str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
