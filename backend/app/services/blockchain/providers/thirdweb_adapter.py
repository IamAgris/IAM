"""OD-23 free-only thirdweb adapter — READ and PREPARE only.

No method in this module signs, broadcasts or pays. The secret key is read from a
Docker secret through its environment-variable NAME and is never returned, logged
or placed in a response. A paid feature is refused, never auto-enabled.
"""

from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.core.secrets import read_secret
from app.services.blockchain.providers.base import (
    ProviderDenied,
    ProviderResponse,
    require_flag,
    require_free_tier,
)


class ThirdwebReadAdapter:
    name = "thirdweb"

    def policy(self) -> Dict[str, Any]:
        return {
            "provider": self.name,
            "free_only": True,
            "paid_plans_allowed": False,
            "read_enabled": settings.thirdweb_read_enabled,
            "execution_enabled": False,
            "credentials_are_env_var_names": True,
            "client_id_env": settings.blockchain_client_id_env,
            "secret_env": settings.blockchain_secret_env,
        }

    def configured(self) -> bool:
        return bool(settings.thirdweb_base_url) and bool(
            read_secret(settings.blockchain_client_id_env)
        )

    async def get_info(self) -> ProviderResponse:
        return ProviderResponse(
            provider=self.name,
            operation="get_info",
            data={
                **self.policy(),
                "configured": self.configured(),
                "available": settings.thirdweb_read_enabled and self.configured(),
                "network_calls_made": False,
            },
            network_calls_made=False,
        )

    async def _rpc(self, method: str, params: list) -> ProviderResponse:  # type: ignore[type-arg]
        require_flag(settings.thirdweb_read_enabled, "thirdweb read adapter is disabled")
        if not self.configured():
            raise ProviderDenied("thirdweb adapter is not configured; set operator-reviewed base URL and client id")
        require_free_tier(self.name, method)

        client_id = read_secret(settings.blockchain_client_id_env)
        headers = {"Content-Type": "application/json", "X-Client-Id": client_id}
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        async with httpx.AsyncClient(timeout=settings.web3_request_timeout_seconds) as client:
            response = await client.post(settings.thirdweb_base_url, json=payload, headers=headers)  # type: ignore[arg-type]
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

    async def get_balance(
        self, address: str, chain_id: Optional[str] = None
    ) -> ProviderResponse:
        if not address or not isinstance(address, str):
            raise ProviderDenied("a valid address is required")
        result = await self._rpc("eth_getBalance", [address, "latest"])
        return ProviderResponse(
            provider=self.name,
            operation="get_balance",
            data={"address": address, "chain_id": chain_id, **result.data},
            network_calls_made=result.network_calls_made,
        )

    async def get_block(
        self, block_ref: str, chain_id: Optional[str] = None
    ) -> ProviderResponse:
        method = "eth_getBlockByNumber" if block_ref.startswith("0x") else "eth_getBlockByHash"
        result = await self._rpc(method, [block_ref, False])
        return ProviderResponse(
            provider=self.name,
            operation="get_block",
            data={"block_ref": block_ref, "chain_id": chain_id, **result.data},
            network_calls_made=result.network_calls_made,
        )

    async def get_transaction(
        self, tx_hash: str, chain_id: Optional[str] = None
    ) -> ProviderResponse:
        result = await self._rpc("eth_getTransactionByHash", [tx_hash])
        return ProviderResponse(
            provider=self.name,
            operation="get_transaction",
            data={"tx_hash": tx_hash, "chain_id": chain_id, **result.data},
            network_calls_made=result.network_calls_made,
        )

    async def build_transaction(self, payload: Dict[str, Any]) -> ProviderResponse:
        """Prepare a transaction locally; never sign, broadcast or estimate paid gas."""
        require_flag(
            settings.web3_transaction_preparation_enabled,
            "transaction preparation is disabled",
        )
        to_address = payload.get("to_address")
        amount = payload.get("amount")
        if not to_address or not isinstance(to_address, str):
            raise ProviderDenied("to_address is required")
        try:
            value = float(amount)  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ProviderDenied("amount must be numeric") from exc
        if value <= 0:
            raise ProviderDenied("amount must be positive")
        return ProviderResponse(
            provider=self.name,
            operation="build_transaction",
            data={
                "status": "prepared",
                "chain_id": payload.get("chain_id"),
                "to_address": to_address,
                "token": payload.get("token"),
                "amount": value,
                "approval_required": True,
                "execution_enabled": False,
            },
            network_calls_made=False,
        )

    async def broadcast(self, payload: Dict[str, Any]) -> ProviderResponse:
        raise ProviderDenied(
            "broadcast requires signed Creator approval; approval integration is deferred"
        )
