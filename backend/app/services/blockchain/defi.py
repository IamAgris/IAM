"""DeFi research and preparation (proposed Doc 35).

Read and calculate only. Quotes are operator-supplied data; IAM independently
validates them and never assumes liquidity, returns or protocol safety. No swap,
stake, lend or withdraw is submitted by this module.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag


@dataclass(frozen=True)
class SwapQuote:
    protocol: str
    chain_id: str
    token_in: str
    token_out: str
    amount_in: float
    amount_out: float
    gas_usd: float = 0.0
    price_impact_pct: float = 0.0
    verified: bool = False


class DeFiIntelligenceService:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_defi_enabled,
            "execution_enabled": False,
            "protocol_registry": "operator-supplied, unverified by default",
            "read_and_prepare_only": True,
        }

    def compare_swaps(self, quotes: List[Dict[str, Any]]) -> Dict[str, Any]:
        require_flag(settings.web3_defi_enabled, "DeFi intelligence is disabled")
        parsed: List[SwapQuote] = []
        for item in quotes:
            try:
                quote = SwapQuote(
                    protocol=str(item["protocol"]),
                    chain_id=str(item["chain_id"]),
                    token_in=str(item["token_in"]),
                    token_out=str(item["token_out"]),
                    amount_in=float(item["amount_in"]),
                    amount_out=float(item["amount_out"]),
                    gas_usd=float(item.get("gas_usd", 0)),
                    price_impact_pct=float(item.get("price_impact_pct", 0)),
                    verified=bool(item.get("verified", False)),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderDenied(f"invalid swap quote: {exc}") from exc
            if quote.amount_in <= 0 or quote.amount_out < 0:
                raise ProviderDenied("quote amounts must be non-negative and input positive")
            parsed.append(quote)
        if not parsed:
            raise ProviderDenied("at least one quote is required")
        ranked = sorted(
            parsed,
            key=lambda q: (q.amount_out - q.gas_usd) if q.verified else float("-inf"),
            reverse=True,
        )
        best = ranked[0]
        return {
            "quotes": [q.__dict__ for q in parsed],
            "best": best.__dict__,
            "note": "Unverified quotes are ranked last. Net output is indicative only.",
            "execution_enabled": False,
        }

    @staticmethod
    def impermanent_loss(price_ratio: float) -> Dict[str, Any]:
        """IL for a 50/50 pool when the relative price changes by ``price_ratio``."""
        if price_ratio <= 0:
            raise ProviderDenied("price_ratio must be positive")
        import math

        value = 2 * math.sqrt(price_ratio) / (1 + price_ratio) - 1
        return {"price_ratio": price_ratio, "impermanent_loss": round(value, 8)}

    @staticmethod
    def liquidation_risk(
        *, collateral_usd: float, debt_usd: float, threshold: float, price_drop_pct: float
    ) -> Dict[str, Any]:
        if collateral_usd <= 0 or debt_usd < 0 or not 0 < threshold <= 1:
            raise ProviderDenied("invalid collateral, debt or liquidation threshold")
        stressed = collateral_usd * (1 - price_drop_pct / 100)
        ratio = debt_usd / stressed if stressed > 0 else float("inf")
        liquidated = ratio >= threshold
        return {
            "stressed_collateral_usd": round(stressed, 4),
            "debt_usd": debt_usd,
            "threshold": threshold,
            "health_factor": round(threshold / ratio, 6) if ratio > 0 else None,
            "liquidation_risk": "high" if liquidated else "low",
            "note": "Simplified model; oracle, fees and protocol mechanics are not modelled.",
        }

    @staticmethod
    def staking_estimate(
        *, amount: float, apy_pct: float, days: int, compound_days: int = 365
    ) -> Dict[str, Any]:
        if amount <= 0 or days < 1 or compound_days < 1:
            raise ProviderDenied("amount, days and compound_days must be positive")
        periods = days / compound_days
        multiplier = (1 + apy_pct / 100 / compound_days) ** (compound_days * periods)
        return {
            "amount": amount,
            "apy_pct": apy_pct,
            "days": days,
            "estimated_reward": round(amount * (multiplier - 1), 8),
            "note": "Estimate only; not a return guarantee (OD-44).",
        }

    def prepare_action(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Produce a signed-approval-ready record. Never executes the action."""
        require_flag(settings.web3_defi_enabled, "DeFi intelligence is disabled")
        allowed = ("web3.defi.swap", "web3.defi.stake")
        if action not in allowed:
            raise ProviderDenied(f"DeFi action '{action}' is not supported")
        return {
            "status": "prepared",
            "action": action,
            "protocol": payload.get("protocol"),
            "chain_id": payload.get("chain_id"),
            "amount": payload.get("amount"),
            "approval_required": True,
            "execution_enabled": False,
            "note": "Signed Creator approval is required before any execution.",
        }
