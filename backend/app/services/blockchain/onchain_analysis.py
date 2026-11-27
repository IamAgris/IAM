"""Advanced read-only on-chain analysis (proposed Doc 35).

All statistics are computed from operator-supplied observations. No RPC call is
made here and no conclusion is presented as certainty.
"""

import statistics
from typing import Any, Dict, List

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag


class OnChainAnalysisService:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_onchain_analysis_enabled,
            "read_only": True,
            "indicative_only": True,
        }

    def holder_concentration(
        self, *, holders: List[Dict[str, Any]], total_supply: float
    ) -> Dict[str, Any]:
        require_flag(settings.web3_onchain_analysis_enabled, "on-chain analysis is disabled")
        if total_supply <= 0 or not holders:
            raise ProviderDenied("positive total_supply and holders are required")
        balances = []
        for holder in holders:
            try:
                balances.append(float(holder["balance"]))
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderDenied(f"invalid holder balance: {exc}") from exc
        if any(value < 0 for value in balances):
            raise ProviderDenied("holder balances cannot be negative")
        ranked = sorted(balances, reverse=True)
        top10 = sum(ranked[:10]) / total_supply
        return {
            "holders": len(ranked),
            "top10_share": round(min(1.0, top10), 6),
            "concentration": "high" if top10 > 0.5 else "medium" if top10 > 0.25 else "low",
            "note": "Exclude burn and contract addresses before relying on this figure.",
        }

    def anomaly_scores(self, *, values: List[float], threshold: float = 2.0) -> Dict[str, Any]:
        require_flag(settings.web3_onchain_analysis_enabled, "on-chain analysis is disabled")
        if len(values) < 3:
            raise ProviderDenied("at least three observations are required")
        mean = statistics.fmean(values)
        deviation = statistics.pstdev(values)
        if deviation == 0:
            return {"mean": mean, "deviation": 0, "anomalies": []}
        anomalies = [
            {"index": index, "value": value, "z_score": round((value - mean) / deviation, 4)}
            for index, value in enumerate(values)
            if abs((value - mean) / deviation) >= threshold
        ]
        return {"mean": mean, "deviation": deviation, "anomalies": anomalies}

    @staticmethod
    def eip1559_fee(base_fee: float, priority_fee: float) -> Dict[str, Any]:
        if base_fee < 0 or priority_fee < 0:
            raise ProviderDenied("fees cannot be negative")
        return {
            "max_fee_per_gas": round(base_fee * 2 + priority_fee, 6),
            "max_priority_fee_per_gas": priority_fee,
            "note": "Estimate only; re-check network conditions before signing.",
        }

    def whale_activity(
        self, *, transfers: List[Dict[str, Any]], threshold: float
    ) -> Dict[str, Any]:
        require_flag(settings.web3_onchain_analysis_enabled, "on-chain analysis is disabled")
        if threshold <= 0:
            raise ProviderDenied("threshold must be positive")
        flagged = []
        for transfer in transfers:
            try:
                amount = float(transfer["amount"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderDenied(f"invalid transfer amount: {exc}") from exc
            if amount >= threshold:
                flagged.append(
                    {
                        "from": transfer.get("from"),
                        "to": transfer.get("to"),
                        "amount": amount,
                        "token": transfer.get("token"),
                    }
                )
        return {"threshold": threshold, "flagged": flagged, "count": len(flagged)}
