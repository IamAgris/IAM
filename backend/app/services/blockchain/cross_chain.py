"""Cross-chain research and bridge preparation (proposed Doc 35).

Routes and quotes are operator-supplied. No bridge transaction is submitted and
no asset is assumed to arrive; settlement must always be verified on the
destination chain.
"""

from typing import Any, Dict, List

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag


class CrossChainService:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_cross_chain_enabled,
            "execution_enabled": False,
            "settlement_verification_required": True,
            "provider_independent": True,
        }

    def compare_routes(self, routes: List[Dict[str, Any]]) -> Dict[str, Any]:
        require_flag(settings.web3_cross_chain_enabled, "cross-chain capability is disabled")
        parsed = []
        for route in routes:
            try:
                parsed.append(
                    {
                        "bridge": str(route["bridge"]),
                        "from_chain": str(route["from_chain"]),
                        "to_chain": str(route["to_chain"]),
                        "amount_out": float(route["amount_out"]),
                        "fee_usd": float(route.get("fee_usd", 0)),
                        "eta_seconds": int(route.get("eta_seconds", 0)),
                        "verified": bool(route.get("verified", False)),
                    }
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ProviderDenied(f"invalid bridge route: {exc}") from exc
        if not parsed:
            raise ProviderDenied("at least one route is required")
        ranked = sorted(
            parsed,
            key=lambda r: (r["amount_out"] - r["fee_usd"]) if r["verified"] else float("-inf"),
            reverse=True,
        )
        return {"routes": parsed, "best": ranked[0], "execution_enabled": False}

    def prepare_bridge(
        self,
        *,
        bridge: str,
        from_chain: str,
        to_chain: str,
        token: str,
        amount: float,
        recipient: str,
    ) -> Dict[str, Any]:
        require_flag(settings.web3_cross_chain_enabled, "cross-chain capability is disabled")
        if amount <= 0 or not recipient:
            raise ProviderDenied("positive amount and recipient are required")
        return {
            "status": "prepared",
            "bridge": bridge,
            "from_chain": from_chain,
            "to_chain": to_chain,
            "token": token,
            "amount": amount,
            "recipient": recipient,
            "approval_action": "web3.bridge.execute",
            "approval_required": True,
            "execution_enabled": False,
            "note": "Bridge settlement must be verified on the destination chain.",
        }

    def settlement_check(
        self, *, from_tx: str, to_tx: str | None, confirmations: int
    ) -> Dict[str, Any]:
        require_flag(settings.web3_cross_chain_enabled, "cross-chain capability is disabled")
        complete = bool(to_tx) and confirmations > 0
        return {
            "from_tx": from_tx,
            "to_tx": to_tx,
            "confirmations": confirmations,
            "settled": complete,
            "note": "A timeout is not proof of failure; verify on-chain before retries.",
        }
