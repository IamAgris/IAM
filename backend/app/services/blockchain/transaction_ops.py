"""Transaction operations: nonce, gas, queue, simulation and stuck recovery.

All outputs are preparations. Nothing is broadcast and no wallet state is mutated
on a real network.
"""

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag


class NonceManager:
    def __init__(self) -> None:
        self._nonces: Dict[str, int] = {}

    @staticmethod
    def key(chain_id: str, address: str) -> str:
        return f"{chain_id}:{address.lower()}"

    def next_nonce(self, chain_id: str, address: str, observed: Optional[int] = None) -> int:
        key = self.key(chain_id, address)
        current = max(self._nonces.get(key, 0), observed or 0)
        self._nonces[key] = current
        return current

    def mark_used(self, chain_id: str, address: str, nonce: int) -> None:
        key = self.key(chain_id, address)
        if nonce < self._nonces.get(key, 0):
            raise ProviderDenied("nonce is below the tracked nonce; possible replay")
        self._nonces[key] = nonce + 1

    def conflicts(self, chain_id: str, address: str, nonces: List[int]) -> List[int]:
        key = self.key(chain_id, address)
        return sorted({n for n in nonces if n < self._nonces.get(key, 0)})


class GasManager:
    @staticmethod
    def estimate(
        *, base_fee: float, priority_fee: float, gas_units: int, budget_usd: float, price_usd: float
    ) -> Dict[str, Any]:
        if min(base_fee, priority_fee, gas_units, budget_usd, price_usd) < 0:
            raise ProviderDenied("gas inputs cannot be negative")
        max_fee = base_fee * 2 + priority_fee
        cost_usd = max_fee * gas_units * price_usd
        return {
            "max_fee_per_gas": round(max_fee, 9),
            "estimated_cost_usd": round(cost_usd, 6),
            "within_budget": cost_usd <= budget_usd,
            "execution_enabled": False,
        }

    @staticmethod
    def replacement_fee(previous_fee: float, increase_pct: float = 10.0) -> float:
        if previous_fee <= 0 or increase_pct <= 0:
            raise ProviderDenied("previous_fee and increase_pct must be positive")
        return round(previous_fee * (1 + increase_pct / 100), 9)


class TransactionQueue:
    def __init__(self) -> None:
        self._items: Dict[str, Dict[str, Any]] = {}

    def enqueue(self, key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        require_flag(settings.web3_transaction_preparation_enabled, "preparation is disabled")
        if key in self._items:
            raise ProviderDenied("idempotency key already queued")
        self._items[key] = {**payload, "status": "queued"}
        return {"idempotency_key": key, "status": "queued"}

    def list(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        return [
            item for item in self._items.values() if not status or item.get("status") == status
        ]

    def transition(self, key: str, status: str) -> Dict[str, Any]:
        allowed = {"queued", "prepared", "awaiting_approval", "approved", "broadcast", "failed"}
        if status not in allowed:
            raise ProviderDenied("unknown queue status")
        item = self._items.get(key)
        if not item:
            raise LookupError("queued transaction not found")
        item["status"] = status
        return {"idempotency_key": key, "status": status}


class TransactionSimulator:
    def simulate(
        self,
        *,
        chain_id: str,
        to_address: str,
        amount: float,
        risk_flags: Optional[List[str]] = None,
        gas_usd: float = 0,
    ) -> Dict[str, Any]:
        require_flag(settings.web3_transaction_preparation_enabled, "preparation is disabled")
        if not to_address or amount <= 0:
            raise ProviderDenied("to_address and positive amount are required")
        flags = list(risk_flags or [])
        blocking = [
            flag
            for flag in flags
            if flag in ("unlimited_approval", "denylisted_recipient", "malicious_contract")
        ]
        return {
            "chain_id": chain_id,
            "to_address": to_address,
            "amount": amount,
            "gas_usd": gas_usd,
            "risk_flags": flags,
            "verdict": "deny" if blocking else "proceed_to_approval",
            "execution_enabled": False,
        }


class StuckTransactionRecovery:
    @staticmethod
    def assess(*, status: str, has_tx_hash: bool, age_minutes: int, threshold_minutes: int) -> Dict[str, Any]:
        stuck = status == "broadcast" and not has_tx_hash and age_minutes >= threshold_minutes
        return {
            "stuck": stuck,
            "suggested_action": "verify on-chain state before any replacement" if stuck else "none",
            "replacement_fee": GasManager.replacement_fee(1.0) if stuck else None,
            "auto_retry": False,
        }
