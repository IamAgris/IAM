"""Unified read-only Bitcoin/Lightning intelligence (proposed Doc 30).

LND and CLN are reported independently. The comparison view never merges node
identities, channels, balances or payment histories and never routes between them.
"""

from typing import Any, Dict, List

from app.core.config import settings
from app.services.blockchain.providers.bitcoin_core_adapter import BitcoinCoreAdapter
from app.services.blockchain.providers.cln_adapter import ClnAdapter
from app.services.blockchain.providers.lnd_adapter import LndAdapter


def _sats(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _outbound(channels_payload: Any) -> int:
    """Best-effort outbound liquidity from either node's channel response."""
    if not isinstance(channels_payload, dict):
        return 0
    channels = channels_payload.get("channels") or channels_payload or []
    if isinstance(channels, dict):
        channels = list(channels.values())
    total = 0
    for channel in channels if isinstance(channels, list) else []:
        if not isinstance(channel, dict):
            continue
        for key in ("local_balance", "local_balance_sats", "localBalance"):
            if key in channel:
                total += _sats(channel[key])
                break
    return total


class NodeService:
    def __init__(self):
        self.bitcoin = BitcoinCoreAdapter()
        self.lnd = LndAdapter()
        self.cln = ClnAdapter()

    def policy(self) -> Dict[str, Any]:
        return {
            "bitcoin_core_enabled": settings.bitcoin_core_read_enabled,
            "lnd_enabled": settings.lnd_read_enabled,
            "cln_enabled": settings.cln_read_enabled,
            "identities_merged": False,
            "execution_enabled": False,
            "transport": "tailscale",
        }

    async def bitcoin_report(self) -> Dict[str, Any]:
        if not settings.bitcoin_core_read_enabled:
            return {"enabled": False, "reason": "Bitcoin Core read adapter is disabled"}
        info = await self.bitcoin.get_info()
        if not info.data.get("available"):
            return {"enabled": True, "configured": False, "reason": "connector not configured"}
        chain = await self.bitcoin.get_blockchain_info()
        mempool = await self.bitcoin.get_mempool_info()
        fees = await self.bitcoin.estimate_fee()
        return {
            "enabled": True,
            "configured": True,
            "blockchain_info": chain.data.get("result"),
            "mempool_info": mempool.data.get("result"),
            "fee_estimate": fees.data.get("result"),
            "execution_enabled": False,
        }

    async def _lightning_node(self, adapter) -> Dict[str, Any]:
        info = await adapter.get_info()
        if not info.data.get("available"):
            return {"configured": False, "reason": "node adapter not configured"}
        node = await adapter.get_node_info()
        balance = await adapter.get_balance()
        channels = await adapter.get_channels()
        peers = await adapter.get_peers()
        return {
            "configured": True,
            "provider": adapter.name,
            "node_info": node.data.get("result"),
            "balance": balance.data.get("result"),
            "channels": channels.data.get("result"),
            "peers": peers.data.get("result"),
            "outbound_liquidity_sats": _outbound(channels.data.get("result")),
        }

    async def lightning_report(self) -> Dict[str, Any]:
        lnd = (
            await self._lightning_node(self.lnd)
            if settings.lnd_read_enabled
            else {"enabled": False, "reason": "LND read adapter is disabled"}
        )
        cln = (
            await self._lightning_node(self.cln)
            if settings.cln_read_enabled
            else {"enabled": False, "reason": "CLN read adapter is disabled"}
        )
        return {
            "lnd": lnd,
            "cln": cln,
            "identities_merged": False,
            "execution_enabled": False,
        }

    async def compare(self) -> Dict[str, Any]:
        """Comparison only: never a merged node and never an auto-routing decision."""
        report = await self.lightning_report()
        candidates: List[Dict[str, Any]] = []
        for name in ("lnd", "cln"):
            node = report[name]
            if node.get("configured"):
                candidates.append(
                    {
                        "node": name,
                        "outbound_liquidity_sats": node["outbound_liquidity_sats"],
                    }
                )
        candidates.sort(key=lambda item: item["outbound_liquidity_sats"], reverse=True)
        return {
            "candidates": candidates,
            "identities_merged": False,
            "auto_routing_enabled": False,
            "note": "Comparison of independent nodes; no shared wallet or channel state.",
        }

    async def health(self) -> Dict[str, Any]:
        return {
            "bitcoin_core": (await self.bitcoin.get_info()).as_dict(),
            "lnd": (await self.lnd.get_info()).as_dict(),
            "cln": (await self.cln.get_info()).as_dict(),
            "network_calls_made": False,
        }
