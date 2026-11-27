"""Web3 accounting: cost basis, realised/unrealised P&L and fee attribution.

Pure calculations over operator-supplied records. Nothing is written to the
financial ledger here; that remains the existing ``LedgerService``.
"""

from typing import Any, Dict, List

from app.services.blockchain.providers.base import ProviderDenied


class Web3AccountingService:
    @staticmethod
    def fifo_basis(lots: List[Dict[str, Any]], quantity: float) -> Dict[str, Any]:
        if quantity <= 0 or not lots:
            raise ProviderDenied("positive quantity and lots are required")
        remaining = quantity
        cost = 0.0
        consumed: List[Dict[str, Any]] = []
        for lot in sorted(lots, key=lambda item: str(item.get("date", ""))):
            available = float(lot.get("quantity", 0))
            if available <= 0:
                continue
            take = min(available, remaining)
            cost += take * float(lot.get("unit_cost", 0))
            consumed.append({"date": lot.get("date"), "quantity": take})
            remaining -= take
            if remaining <= 0:
                break
        if remaining > 0:
            raise ProviderDenied("insufficient lots to cover the quantity")
        return {"quantity": quantity, "cost_basis": round(cost, 8), "consumed": consumed}

    @staticmethod
    def realised_pnl(*, proceeds: float, cost_basis: float, fees: float = 0.0) -> Dict[str, Any]:
        return {
            "proceeds": proceeds,
            "cost_basis": cost_basis,
            "fees": fees,
            "realised_pnl": round(proceeds - cost_basis - fees, 8),
        }

    @staticmethod
    def unrealised_pnl(*, quantity: float, cost_basis: float, mark_price: float) -> Dict[str, Any]:
        if quantity < 0 or mark_price < 0:
            raise ProviderDenied("quantity and mark_price cannot be negative")
        value = quantity * mark_price
        return {
            "market_value": round(value, 8),
            "cost_basis": round(cost_basis, 8),
            "unrealised_pnl": round(value - cost_basis, 8),
        }

    @staticmethod
    def portfolio_exposure(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = 0.0
        for item in holdings:
            try:
                total += float(item.get("value_usd", 0))
            except (TypeError, ValueError) as exc:
                raise ProviderDenied("holding values must be numeric") from exc
        if total <= 0:
            raise ProviderDenied("positive portfolio value is required")
        rows = [
            {
                "asset": item.get("asset"),
                "value_usd": float(item.get("value_usd", 0)),
                "share": round(float(item.get("value_usd", 0)) / total, 6),
            }
            for item in holdings
        ]
        return {"total_usd": round(total, 4), "holdings": rows}
