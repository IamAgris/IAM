"""Prepare-only transaction manager (proposed Doc 35 §6.1).

This module deliberately stops at ``simulated``. Moving a record to
``awaiting_approval``/``approved`` and any broadcast/payment operation require
Creator approval integration, which is a separate later work item. There is no
path from this module to a signed or broadcast transaction.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.web3 import Web3Transaction
from app.services.blockchain.audit import BlockchainAuditService
from app.services.blockchain.governance import (
    ExecutionAuthorization,
    Web3ApprovalService,
)
from app.services.blockchain.network_registry import NetworkRegistry
from app.services.blockchain.providers.base import ProviderDenied, require_flag

TERMINAL = frozenset({"reconciled", "rejected", "expired", "failed", "replaced", "cancelled"})


class TransactionExecutor(Protocol):
    """Protected signing infrastructure — IAM never holds the signing key."""

    async def submit(
        self, authorization: ExecutionAuthorization, payload: Dict[str, Any]
    ) -> Dict[str, Any]: ...


class NoExecutor:
    """Default: no signing infrastructure configured, so no execution is possible."""

    async def submit(
        self, authorization: ExecutionAuthorization, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        raise ProviderDenied(
            "no protected signing executor is configured; set an operator-reviewed "
            "web3_executor_url before execution can be requested"
        )


class HttpExecutor:
    """Delegates signing to an external protected service. Sends no keys."""

    def __init__(self, url: str):
        self.url = url

    async def submit(
        self, authorization: ExecutionAuthorization, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=settings.web3_request_timeout_seconds) as client:
            response = await client.post(
                self.url,
                json={
                    "authorization": authorization.summary(),
                    "transaction": payload,
                },
            )
            response.raise_for_status()
            _typed_result: dict[str, Any] = response.json()
            return _typed_result


def _executor() -> TransactionExecutor:
    if settings.web3_executor_url:
        return HttpExecutor(settings.web3_executor_url)
    return NoExecutor()


def idempotency_key(payload: Dict[str, Any]) -> str:
    material = json.dumps(
        {
            "chain_id": str(payload.get("chain_id", "")),
            "from": payload.get("from_address", ""),
            "to": payload.get("to_address", ""),
            "token": payload.get("token", ""),
            "amount": str(payload.get("amount", "")),
            "nonce": str(payload.get("nonce", "")),
            "approval_id": payload.get("approval_id", ""),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class TransactionManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.networks = NetworkRegistry()
        self.approvals = Web3ApprovalService(db)

    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_transaction_preparation_enabled,
            "execution_enabled": settings.web3_execution_enabled,
            "executor_configured": bool(settings.web3_executor_url),
            "creator_approval_integration": "enabled",
            "approval_engine": "CreatorApprovalService",
            "highest_reachable_state": "broadcast",
            "reverify_at_execution": True,
            "iam_holds_signing_key": False,
        }

    async def _audit(self, event: str, actor: str, target: str, details: Dict[str, Any]) -> None:
        if settings.web3_audit_enabled:
            await BlockchainAuditService(self.db).append(
                event_type=event, actor=actor, target=target, details=details
            )

    async def prepare(self, payload: Dict[str, Any], actor: str = "iam") -> Dict[str, Any]:
        """Validate and record a prepared transaction. Never signs or broadcasts."""
        require_flag(
            settings.web3_transaction_preparation_enabled,
            "transaction preparation is disabled",
        )
        chain_id = str(payload.get("chain_id", ""))
        self.networks.require_capability(chain_id, "prepare_transaction")
        to_address = payload.get("to_address")
        if not to_address or not isinstance(to_address, str):
            raise ProviderDenied("to_address is required")
        try:
            amount = float(payload.get("amount"))  # type: ignore[arg-type]
        except (TypeError, ValueError) as exc:
            raise ProviderDenied("amount must be numeric") from exc
        if amount <= 0:
            raise ProviderDenied("amount must be positive")

        key = idempotency_key(payload)
        result = await self.db.execute(select(Web3Transaction))
        existing = next(
            (row for row in result.scalars().all() if row.idempotency_key == key), None
        )
        if existing:
            return {
                "id": str(existing.id),
                "idempotency_key": key,
                "status": existing.status,
                "duplicate_of": str(existing.id),
            }

        network = self.networks.get_network(chain_id)
        simulation = {
            "chain_id": chain_id,
            "testnet": network["testnet"],
            "production_gated": network["production_gated"],
            "confirmation_blocks": network["confirmation_blocks"],
            "amount": amount,
            "to_address": to_address,
            "approval_required": True,
            "execution_enabled": False,
        }
        row = Web3Transaction(
            approval_id=payload.get("approval_id"),
            wallet_id=payload.get("wallet_id"),
            chain_id=chain_id,
            tx_type=payload.get("tx_type", "transfer"),
            from_address=payload.get("from_address"),
            to_address=to_address,
            token=payload.get("token"),
            amount=amount,
            gas_estimate=payload.get("gas_estimate"),
            status="simulated",
            idempotency_key=key,
            simulation=simulation,
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(
            "web3_transaction_prepared", actor, str(row.id),
            {"chain_id": chain_id, "to_address": to_address, "amount": amount},
        )
        await self.db.commit()
        return {
            "id": str(row.id),
            "idempotency_key": key,
            "status": row.status,
            "approval_required": True,
            "execution_enabled": False,
        }

    async def list_transactions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(Web3Transaction))
        return [
            {
                "id": str(row.id),
                "chain_id": row.chain_id,
                "to_address": row.to_address,
                "amount": float(row.amount) if row.amount is not None else None,
                "status": row.status,
                "tx_hash": row.tx_hash,
            }
            for row in result.scalars().all()
            if not status or row.status == status
        ]

    async def request_approval(
        self, transaction_id: str, channel: str = "creator_cli", actor: str = "iam"
    ) -> Dict[str, Any]:
        """Create a PENDING Creator request. Never grants authority by itself."""
        require_flag(
            settings.web3_transaction_preparation_enabled,
            "transaction preparation is disabled",
        )
        row = await self._get(transaction_id)
        if row.status != "simulated":
            raise ProviderDenied(f"cannot request approval from state {row.status}")
        request = await self.approvals.create_request(
            action="web3.transaction.broadcast",
            target_ref=transaction_id,
            summary=(
                f"Broadcast prepared {row.chain_id} transaction to {row.to_address} "
                f"for {row.amount}"
            ),
            reason="IAM prepared a transaction and requests signed Creator authority",
            channel=channel,
            requester=actor,
        )
        previous = row.status
        row.status = "awaiting_approval"  # type: ignore[assignment]
        simulation = dict(row.simulation or {})
        simulation["creator_request_id"] = request.get("request_id")
        row.simulation = simulation  # type: ignore[assignment]
        await self.db.flush()
        await self._audit(
            "web3_approval_requested", actor, transaction_id,
            {"request_id": request.get("request_id"), "from": previous},
        )
        await self.db.commit()
        return {
            "transaction_id": transaction_id,
            "request_id": request.get("request_id"),
            "challenge_hash": request.get("challenge_hash"),
            "status": "awaiting_approval",
            "plain_reply_authorises": False,
        }

    async def confirm_approval(
        self, transaction_id: str, approval_id: str, amount_usd: float
    ) -> Dict[str, Any]:
        """Verify the signed decision and move to ``approved``. No broadcast here."""
        require_flag(
            settings.web3_transaction_preparation_enabled,
            "transaction preparation is disabled",
        )
        row = await self._get(transaction_id)
        if row.status != "awaiting_approval":
            raise ProviderDenied(f"cannot confirm approval from state {row.status}")
        authorization = await self.approvals.authorize(
            action="web3.transaction.broadcast",
            approval_id=approval_id,
            amount_usd=amount_usd,
            target_ref=transaction_id,
        )
        previous = row.status
        row.status = "approved"  # type: ignore[assignment]
        row.approval_id = approval_id  # type: ignore[assignment]
        simulation = dict(row.simulation or {})
        simulation["amount_usd"] = float(amount_usd)
        row.simulation = simulation  # type: ignore[assignment]
        await self.db.flush()
        await self._audit(
            "web3_approval_confirmed", "creator", transaction_id,
            {"from": previous, "authorization_id": authorization.authorization_id},
        )
        await self.db.commit()
        return {
            "transaction_id": transaction_id,
            "status": "approved",
            "authorization_id": authorization.authorization_id,
            "broadcast": False,
        }

    async def broadcast(
        self, transaction_id: str, amount_usd: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute only after re-verifying signed authority at execution time."""
        require_flag(settings.web3_execution_enabled, "Web3 execution is disabled")
        row = await self._get(transaction_id)
        if row.status != "approved" or not row.approval_id:
            raise ProviderDenied("transaction is not in the approved state")
        valuation = amount_usd if amount_usd is not None else dict(row.simulation or {}).get("amount_usd")
        authorization = await self.approvals.authorize(
            action="web3.transaction.broadcast",
            approval_id=row.approval_id,  # type: ignore[arg-type]
            amount_usd=valuation,
            target_ref=transaction_id,
        )
        payload = {
            "chain_id": row.chain_id,
            "from_address": row.from_address,
            "to_address": row.to_address,
            "token": row.token,
            "amount": float(row.amount) if row.amount is not None else None,
            "idempotency_key": row.idempotency_key,
        }
        result = await _executor().submit(authorization, payload)
        previous = row.status
        row.status = "broadcast"  # type: ignore[assignment]
        row.tx_hash = result.get("tx_hash")  # type: ignore[assignment]
        await self.db.flush()
        await self._audit(
            "web3_transaction_broadcast", "creator", transaction_id,
            {"from": previous, "tx_hash": row.tx_hash},
        )
        await self.db.commit()
        return {
            "transaction_id": transaction_id,
            "status": "broadcast",
            "tx_hash": row.tx_hash,
            "executor": result.get("executor"),
        }

    async def _get(self, transaction_id: str) -> Web3Transaction:
        result = await self.db.execute(select(Web3Transaction))
        row = next(
            (item for item in result.scalars().all() if str(item.id) == str(transaction_id)),
            None,
        )
        if not row:
            raise LookupError("transaction not found")
        return row
