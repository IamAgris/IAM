"""Read-only Bitcoin Core adapter through an in-Umbrel connector.

RPC credentials are read from a Docker secret through their environment-variable
NAME. The connector exposes only the allowlisted read methods below; no wallet
spending or transaction broadcasting method is reachable from IAM.
"""

from typing import Any, Dict

import httpx

from app.core.config import settings
from app.core.secrets import read_secret
from app.services.blockchain.providers.base import (
    ProviderDenied,
    ProviderResponse,
    require_flag,
)

READ_METHODS = frozenset(
    {
        "getblockchaininfo",
        "getnetworkinfo",
        "getmempoolinfo",
        "getblockhash",
        "getblock",
        "getrawtransaction",
        "estimatesmartfee",
        "gettxout",
    }
)


class BitcoinCoreAdapter:
    name = "bitcoin_core"

    def policy(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "network": "mainnet",
            "read_enabled": settings.bitcoin_core_read_enabled,
            "allowed_methods": sorted(READ_METHODS),
            "broadcast_enabled": False,
            "credentials_are_env_var_names": True,
            "cookie_env": settings.bitcoin_core_cookie_env,
            "transport": "tailscale",
        }

    def configured(self) -> bool:
        return bool(settings.bitcoin_core_connector_url) and bool(
            read_secret(settings.bitcoin_core_cookie_env)
        )

    async def get_info(self) -> ProviderResponse:
        return ProviderResponse(
            provider=self.name,
            operation="get_info",
            data={
                **self.policy(),
                "configured": self.configured(),
                "available": settings.bitcoin_core_read_enabled and self.configured(),
                "network_calls_made": False,
            },
        )

    async def _rpc(self, method: str, params: list) -> ProviderResponse:  # type: ignore[type-arg]
        require_flag(settings.bitcoin_core_read_enabled, "Bitcoin Core read adapter is disabled")
        if method not in READ_METHODS:
            raise ProviderDenied(
                f"Bitcoin RPC method '{method}' is not in the read-only allowlist"
            )
        if not self.configured():
            raise ProviderDenied("Bitcoin Core connector is not configured")
        cookie = read_secret(settings.bitcoin_core_cookie_env) or ""
        user, _, password = cookie.partition(":")
        auth = httpx.BasicAuth(user, password)
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        async with httpx.AsyncClient(timeout=settings.web3_request_timeout_seconds) as client:
            response = await client.post(
                settings.bitcoin_core_connector_url, json=payload, auth=auth
            )
            response.raise_for_status()
            body = response.json()
        if body.get("error"):
            return ProviderResponse(
                provider=self.name,
                operation=method,
                data={"rpc_error": str(body["error"])[:500]},
                network_calls_made=True,
            )
        return ProviderResponse(
            provider=self.name,
            operation=method,
            data={"result": body.get("result")},
            network_calls_made=True,
        )

    async def get_blockchain_info(self) -> ProviderResponse:
        return await self._rpc("getblockchaininfo", [])

    async def get_mempool_info(self) -> ProviderResponse:
        return await self._rpc("getmempoolinfo", [])

    async def get_transaction(self, txid: str) -> ProviderResponse:
        result = await self._rpc("getrawtransaction", [txid, True])
        return ProviderResponse(
            provider=self.name,
            operation="get_transaction",
            data={"txid": txid, **result.data},
            network_calls_made=result.network_calls_made,
        )

    async def estimate_fee(self, confirmations: int = 6) -> ProviderResponse:
        return await self._rpc("estimatesmartfee", [confirmations])

    async def broadcast(self, payload: Dict[str, Any]) -> ProviderResponse:
        raise ProviderDenied(
            "Bitcoin transaction broadcasting requires signed Creator approval; "
            "approval integration is deferred"
        )
