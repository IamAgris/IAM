"""Per-network capability registry (proposed Doc 35 §5.2).

A network is not assumed supported because a provider advertises it. Every
(provider, network, method) capability is explicit and unverified capabilities
fail closed. Mainnet entries are production-gated and never imply spend authority.
"""

from typing import Any, Dict, List, Optional

from app.services.blockchain.providers.base import ProviderDenied


def _network(chain_id, name, currency, *, testnet, confirmations, methods):
    return {
        "chain_id": chain_id,
        "name": name,
        "native_currency": currency,
        "testnet": testnet,
        "production_gated": not testnet,
        "free_tier_verified": testnet,
        "confirmation_blocks": confirmations,
        "methods": tuple(methods),
    }


NETWORKS: Dict[str, Dict[str, Any]] = {
    "11155111": _network("11155111", "sepolia", "ETH", testnet=True, confirmations=4,
                         methods=("read_balance", "read_block", "read_transaction", "prepare_transaction")),
    "84532": _network("84532", "base-sepolia", "ETH", testnet=True, confirmations=4,
                      methods=("read_balance", "read_block", "read_transaction", "prepare_transaction")),
    "80001": _network("80001", "mumbai", "MATIC", testnet=True, confirmations=4,
                      methods=("read_balance", "read_block", "read_transaction")),
    "97": _network("97", "bsc-testnet", "BNB", testnet=True, confirmations=6,
                   methods=("read_balance", "read_block", "read_transaction")),
    "1": _network("1", "ethereum", "ETH", testnet=False, confirmations=12, methods=("read_balance",)),
    "8453": _network("8453", "base", "ETH", testnet=False, confirmations=6, methods=("read_balance",)),
    "42161": _network("42161", "arbitrum", "ETH", testnet=False, confirmations=12, methods=("read_balance",)),
    "10": _network("10", "optimism", "ETH", testnet=False, confirmations=12, methods=("read_balance",)),
    "137": _network("137", "polygon", "POL", testnet=False, confirmations=64, methods=("read_balance",)),
    "56": _network("56", "bsc", "BNB", testnet=False, confirmations=15, methods=("read_balance",)),
    "43114": _network("43114", "avalanche", "AVAX", testnet=False, confirmations=12, methods=("read_balance",)),
}


class NetworkRegistry:
    """Read-only view of verified network capabilities and their limitations."""

    def list_networks(self, *, testnet_only: bool = False) -> List[Dict[str, Any]]:
        return [
            {**entry, "methods": list(entry["methods"])}
            for entry in NETWORKS.values()
            if not testnet_only or entry["testnet"]
        ]

    def get_network(self, chain_id: str) -> Dict[str, Any]:
        entry = NETWORKS.get(str(chain_id))
        if not entry:
            raise ProviderDenied(f"chain {chain_id} is not in the capability registry")
        return {**entry, "methods": list(entry["methods"])}

    def capability(self, chain_id: str, method: str) -> Dict[str, Any]:
        entry = self.get_network(chain_id)
        allowed = method in entry["methods"]
        return {
            "chain_id": str(chain_id),
            "method": method,
            "allowed": allowed,
            "reason": None if allowed else "capability not verified for this network",
            "production_gated": entry["production_gated"],
        }

    def require_capability(self, chain_id: str, method: str) -> None:
        if not self.capability(chain_id, method)["allowed"]:
            raise ProviderDenied(
                f"capability '{method}' is not verified on chain {chain_id}"
            )

    @staticmethod
    def free_only(chain_id: str) -> bool:
        return NETWORKS.get(str(chain_id), {}).get("free_tier_verified", False)
