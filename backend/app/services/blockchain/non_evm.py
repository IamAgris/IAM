"""Non-EVM and emerging-network research registry (proposed Doc 35).

Capabilities are unverified until tested. Bitcoin is already represented by the
separate self-hosted node adapter and is not treated as an EVM chain here.
"""

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag

NETWORKS = (
    {"name": "solana", "family": "non_evm", "adapter": "research_only", "verified": False},
    {"name": "bitcoin", "family": "utxo", "adapter": "umbrel_bitcoin_core", "verified": False},
    {"name": "base", "family": "l2_rollup", "adapter": "thirdweb_evm", "verified": False},
    {"name": "arbitrum", "family": "l2_rollup", "adapter": "thirdweb_evm", "verified": False},
    {"name": "optimism", "family": "l2_rollup", "adapter": "thirdweb_evm", "verified": False},
    {"name": "polygon_zkevm", "family": "zk_rollup", "adapter": "research_only", "verified": False},
    {"name": "starknet", "family": "zk_rollup", "adapter": "research_only", "verified": False},
    {"name": "ibc", "family": "interoperability", "adapter": "research_only", "verified": False},
    {"name": "layerzero", "family": "cross_chain_messaging", "adapter": "research_only", "verified": False},
    {"name": "did", "family": "identity_standard", "adapter": "research_only", "verified": False},
)


class NonEvmRegistry:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_registry_enabled,
            "enable_only_after_verification": True,
            "no_public_rpc_assumed": True,
        }

    def list(self, family: Optional[str] = None) -> List[Dict[str, Any]]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        return [dict(item) for item in NETWORKS if not family or item["family"] == family]

    def capability(self, name: str) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        entry = next((item for item in NETWORKS if item["name"] == name), None)
        if not entry:
            raise ProviderDenied(f"network '{name}' is not registered")
        return {
            **entry,
            "enabled": False,
            "reason": "capability must be verified before enablement",
        }
