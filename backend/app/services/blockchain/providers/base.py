"""Shared contracts for Web3 and node adapters (proposed Doc 35).

Design rule: an adapter may read and prepare, never execute. Execution methods are
declared so that callers get an explicit denial rather than a missing attribute.
Creator approval integration is deliberately deferred.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from app.core.config import settings


class ProviderDenied(PermissionError):
    """Raised for a disabled flag, a paid feature, or any execution attempt."""


@dataclass(frozen=True)
class ProviderResponse:
    """Uniform adapter result; never contains credentials or key material."""

    provider: str
    operation: str
    data: Dict[str, Any] = field(default_factory=dict)
    network_calls_made: bool = False
    read_only: bool = True

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "operation": self.operation,
            "data": self.data,
            "network_calls_made": self.network_calls_made,
            "read_only": self.read_only,
        }


def require_flag(enabled: bool, message: str) -> None:
    """Fail closed when the operator has not enabled this adapter."""
    if not enabled:
        raise ProviderDenied(message)


def require_free_tier(provider: str, feature: str) -> None:
    """OD-23: a paid feature is never silently enabled or upgraded."""
    if feature in PAID_FEATURES:
        raise ProviderDenied(
            f"{provider} feature '{feature}' requires a paid tier; "
            "OD-23 permits free-tier and self-hosted open-source use only"
        )


PAID_FEATURES = frozenset(
    {
        "paid_rpc_capacity",
        "paid_engine",
        "paid_transactions",
        "paid_storage",
        "paid_gas_sponsorship",
        "mainnet_value_transfer",
    }
)


@runtime_checkable
class BlockchainProvider(Protocol):
    name: str

    def policy(self) -> Dict[str, Any]: ...

    def configured(self) -> bool: ...

    async def get_info(self) -> ProviderResponse: ...

    async def get_balance(
        self, address: str, chain_id: Optional[str] = None
    ) -> ProviderResponse: ...

    async def get_block(
        self, block_ref: str, chain_id: Optional[str] = None
    ) -> ProviderResponse: ...

    async def get_transaction(
        self, tx_hash: str, chain_id: Optional[str] = None
    ) -> ProviderResponse: ...

    async def build_transaction(self, payload: Dict[str, Any]) -> ProviderResponse: ...

    async def broadcast(self, payload: Dict[str, Any]) -> ProviderResponse:
        raise ProviderDenied(
            "transaction execution requires signed Creator approval; "
            "approval integration is not enabled in this build"
        )


@runtime_checkable
class LightningProvider(Protocol):
    name: str

    def policy(self) -> Dict[str, Any]: ...

    def configured(self) -> bool: ...

    async def get_node_info(self) -> ProviderResponse: ...

    async def get_balance(self) -> ProviderResponse: ...

    async def get_channels(self) -> ProviderResponse: ...

    async def get_peers(self) -> ProviderResponse: ...

    async def get_invoices(self) -> ProviderResponse: ...

    async def get_payments(self) -> ProviderResponse: ...

    async def create_invoice(self, payload: Dict[str, Any]) -> ProviderResponse:
        raise ProviderDenied(
            "invoice creation requires signed Creator approval; "
            "approval integration is not enabled in this build"
        )

    async def pay_invoice(self, payload: Dict[str, Any]) -> ProviderResponse:
        raise ProviderDenied(
            "payment execution requires signed Creator approval; "
            "approval integration is not enabled in this build"
        )


ADAPTER_TIMEOUT = lambda: settings.web3_request_timeout_seconds
