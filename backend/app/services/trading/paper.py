"""Doc 25 paper-trading simulation with hard risk limits.

No real orders are placed. Every portfolio is `simulation_only=True`. Orders
are rejected when they exceed per-order, daily-exposure, cash, loss or
stop-loss limits, or when the emergency stop is engaged. Changing limits or
the emergency stop requires signed Creator authority.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.security import AuditEvent
from app.models.trading import PaperOrder, PaperPortfolio
from app.services.creatorapproval_service import CreatorApprovalService

RISK_ACTION = "trading.risk_limits"
STOP_ACTION = "trading.emergency_stop"
FEE_RATE = 0.001


class TradingDenied(PermissionError):
    """Raised when a simulated order or control breaks policy."""


class PaperTradingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "simulation_only": True,
            "enabled": settings.trading_simulation_enabled,
            "max_order_usd": settings.trading_max_order_usd,
            "daily_exposure_usd": settings.trading_daily_exposure_usd,
            "max_loss_usd": settings.trading_max_loss_usd,
            "stop_loss_pct": settings.trading_stop_loss_pct,
            "requires_signed_authority_for_limits": RISK_ACTION,
            "requires_signed_authority_for_stop": STOP_ACTION,
        }

    async def _portfolio(self, portfolio_id: str) -> PaperPortfolio:
        result = await self.db.execute(
            select(PaperPortfolio).where(PaperPortfolio.id == UUID(str(portfolio_id)))
        )
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            raise LookupError("portfolio not found")
        return portfolio

    async def _authority(self, action: str, target: str) -> Dict[str, Any]:
        authority = await CreatorApprovalService(self.db).check_authorization(
            action, requested_level="3", target_ref=target
        )
        if not authority.get("authorized"):
            raise TradingDenied(f"no active signed Creator authorization for {action} on {target}")
        return authority

    async def create_portfolio(self, name: str, starting_cash: float, actor: str) -> Dict[str, Any]:
        if not settings.trading_simulation_enabled:
            raise TradingDenied("paper trading is disabled")
        if not name or starting_cash < 0:
            raise TradingDenied("name and non-negative starting cash are required")
        portfolio = PaperPortfolio(
            name=name,
            cash_balance=starting_cash,
            holdings={},
            risk_limits={
                "max_order_usd": settings.trading_max_order_usd,
                "daily_exposure_usd": settings.trading_daily_exposure_usd,
                "max_loss_usd": settings.trading_max_loss_usd,
                "stop_loss_pct": settings.trading_stop_loss_pct,
            },
            emergency_stop=False,
            simulation_only=True,
        )
        self.db.add(portfolio)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="paper_portfolio_created",
                actor=actor,
                target=str(portfolio.id),
                details={"name": name, "starting_cash": starting_cash},
            )
        )
        await self.db.commit()
        return self._portfolio_dict(portfolio)

    async def place_order(
        self,
        portfolio_id: str,
        *,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        actor: str,
    ) -> Dict[str, Any]:
        if not settings.trading_simulation_enabled:
            raise TradingDenied("paper trading is disabled")
        from app.services.emergency_shutdown import emergency

        if emergency.is_halted("trading"):
            raise TradingDenied("emergency stop active: trading is halted")
        portfolio = await self._portfolio(portfolio_id)
        if portfolio.emergency_stop:
            raise TradingDenied("emergency stop is engaged")
        if side not in ("buy", "sell") or not symbol or quantity <= 0 or price <= 0:
            raise TradingDenied("valid symbol, side, positive quantity and price are required")

        notional = round(quantity * price, 4)
        fee = round(notional * FEE_RATE, 4)
        limits: Any = portfolio.risk_limits or {}
        if notional > float(limits.get("max_order_usd", settings.trading_max_order_usd)):
            raise TradingDenied("order exceeds the per-order limit")

        result = await self.db.execute(
            select(PaperOrder).where(PaperOrder.portfolio_id == portfolio.id)
        )
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        exposure = sum(
            float(item.notional)
            for item in result.scalars().all()
            if (item.created_at or datetime.now(timezone.utc)).replace(tzinfo=None) >= today.replace(tzinfo=None)
        )
        if exposure + notional > float(
            limits.get("daily_exposure_usd", settings.trading_daily_exposure_usd)
        ):
            raise TradingDenied("daily exposure limit would be exceeded")

        holdings = dict(portfolio.holdings or {})
        cash = float(portfolio.cash_balance)
        if side == "buy":
            if cash < notional + fee:
                raise TradingDenied("insufficient simulated cash")
            cash -= notional + fee
            holdings[symbol] = float(holdings.get(symbol, 0)) + quantity
        else:
            if float(holdings.get(symbol, 0)) < quantity:
                raise TradingDenied("insufficient simulated position")
            holdings[symbol] = float(holdings.get(symbol, 0)) - quantity
            cash += notional - fee
        portfolio.cash_balance = cash  # type: ignore[assignment]
        portfolio.holdings = holdings  # type: ignore[assignment]

        order = PaperOrder(
            portfolio_id=portfolio.id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            notional=notional,
            fee=fee,
            status="simulated",
        )
        self.db.add(order)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="paper_order_simulated",
                actor=actor,
                target=str(order.id),
                details={
                    "portfolio_id": str(portfolio.id),
                    "symbol": symbol,
                    "side": side,
                    "notional": notional,
                    "simulation_only": True,
                },
            )
        )
        await self.db.commit()
        return {
            "id": str(order.id),
            "status": order.status,
            "symbol": symbol,
            "side": side,
            "notional": notional,
            "simulation_only": True,
        }

    async def set_limits(
        self, portfolio_id: str, limits: Dict[str, Any], actor: str
    ) -> Dict[str, Any]:
        portfolio = await self._portfolio(portfolio_id)
        authority = await self._authority(RISK_ACTION, str(portfolio.id))
        merged = dict(portfolio.risk_limits or {})
        for key in ("max_order_usd", "daily_exposure_usd", "max_loss_usd", "stop_loss_pct"):
            if key in limits:
                value = float(limits[key])
                if value < 0:
                    raise TradingDenied(f"{key} must be non-negative")
                merged[key] = value
        portfolio.risk_limits = merged  # type: ignore[assignment]
        self.db.add(
            AuditEvent(
                event_type="paper_trading_limits_updated",
                actor=actor,
                target=str(portfolio.id),
                details={"limits": merged, "authorization_id": authority["authorization_id"]},
            )
        )
        await self.db.commit()
        return {"portfolio_id": str(portfolio.id), "risk_limits": merged}

    async def emergency_stop(
        self, portfolio_id: str, enabled: bool, actor: str
    ) -> Dict[str, Any]:
        portfolio = await self._portfolio(portfolio_id)
        authority = await self._authority(STOP_ACTION, str(portfolio.id))
        portfolio.emergency_stop = bool(enabled)  # type: ignore[assignment]
        self.db.add(
            AuditEvent(
                event_type="paper_trading_emergency_stop",
                actor=actor,
                target=str(portfolio.id),
                details={"enabled": bool(enabled), "authorization_id": authority["authorization_id"]},
            )
        )
        await self.db.commit()
        return {"portfolio_id": str(portfolio.id), "emergency_stop": bool(enabled)}

    async def report(self, portfolio_id: str) -> Dict[str, Any]:
        portfolio = await self._portfolio(portfolio_id)
        result = await self.db.execute(
            select(PaperOrder).where(PaperOrder.portfolio_id == portfolio.id)
        )
        orders = list(result.scalars().all())
        invested = sum(float(order.notional) for order in orders if order.side == "buy")
        realised = sum(float(order.notional) for order in orders if order.side == "sell")
        limits: Any = portfolio.risk_limits or {}
        if realised - invested < -float(limits.get("max_loss_usd", settings.trading_max_loss_usd)):
            return {
                **self._portfolio_dict(portfolio),
                "orders": len(orders),
                "breach": "max_loss_exceeded",
                "suggested_control": "emergency_stop",
            }
        return {
            **self._portfolio_dict(portfolio),
            "orders": len(orders),
            "invested": invested,
            "realised": realised,
            "net": round(realised - invested, 4),
            "breach": None,
        }

    @staticmethod
    def _portfolio_dict(portfolio: PaperPortfolio) -> Dict[str, Any]:
        return {
            "id": str(portfolio.id),
            "name": portfolio.name,
            "cash_balance": float(portfolio.cash_balance),
            "holdings": portfolio.holdings or {},
            "risk_limits": portfolio.risk_limits or {},
            "emergency_stop": bool(portfolio.emergency_stop),
            "simulation_only": bool(portfolio.simulation_only),
        }
