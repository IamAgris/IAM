"""OD-23 free-only blockchain adapter and activity ledger.

No RPC call is ever made by default. Testnets only, no paid plan or mainnet
unless explicitly unlocked, and any write activity requires a signed Creator
authorization. Tokens are environment-variable names, never stored values.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.business import CryptoActivity
from app.models.security import AuditEvent
from app.services.creatorapproval_service import CreatorApprovalService

TESTNET_CHAINS = {
    "11155111": "sepolia",
    "80001": "mumbai",
    "97": "bsc-testnet",
    "84532": "base-sepolia",
}
WRITE_ACTION = "blockchain.write"


class BlockchainDenied(PermissionError):
    """Raised when a blockchain operation is outside the free/testnet policy."""


class BlockchainService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.blockchain_enabled,
            "provider": settings.blockchain_provider,
            "free_only": True,
            "testnet_chain_id": settings.blockchain_chain_id,
            "allowed_testnets": TESTNET_CHAINS,
            "mainnet_allowed": settings.blockchain_allow_mainnet,
            "paid_plans_allowed": False,
            "write_requires_signed_authorization": WRITE_ACTION,
            "credentials_are_env_var_names": True,
        }

    def status(self) -> Dict[str, Any]:
        configured = bool(settings.blockchain_rpc_url) and all(
            os.environ.get(name)
            for name in (settings.blockchain_client_id_env, settings.blockchain_secret_env)
        )
        return {
            **self.policy(),
            "configured": configured,
            "available": settings.blockchain_enabled and configured,
            "network_calls_made": False,
        }

    async def record_activity(
        self,
        *,
        asset: str,
        amount: float,
        address: str,
        tx_hash: str,
        approval_id: Optional[str],
        actor: str,
    ) -> Dict[str, Any]:
        if not settings.blockchain_enabled:
            raise BlockchainDenied("blockchain adapter is disabled")
        if settings.blockchain_allow_mainnet and settings.blockchain_chain_id not in TESTNET_CHAINS:
            raise BlockchainDenied("mainnet activity is not available in the free-only tier")
        if settings.blockchain_chain_id not in TESTNET_CHAINS:
            raise BlockchainDenied(f"chain {settings.blockchain_chain_id} is not a known free testnet")
        if not asset or amount <= 0 or not address:
            raise BlockchainDenied("asset, positive amount and address are required")
        if not approval_id:
            raise BlockchainDenied("blockchain writes require signed Creator authority")
        authority = await CreatorApprovalService(self.db).check_authorization(
            WRITE_ACTION, requested_level="3", target_ref=str(approval_id)
        )
        if not authority.get("authorized"):
            raise BlockchainDenied("no active signed Creator authorization for this write")

        activity = CryptoActivity(
            blockchain=f"{settings.blockchain_provider}:{settings.blockchain_chain_id}",
            asset=asset,
            amount=amount,
            address=address,
            tx_hash=tx_hash,
            status="pending",
        )
        self.db.add(activity)
        await self.db.flush()
        self.db.add(
            AuditEvent(
                event_type="blockchain_activity_recorded",
                actor=actor,
                target=str(activity.id),
                details={
                    "asset": asset,
                    "amount": amount,
                    "chain_id": settings.blockchain_chain_id,
                    "authorization_id": authority["authorization_id"],
                    "network_calls_made": False,
                },
            )
        )
        await self.db.commit()
        return {
            "id": str(activity.id),
            "chain_id": settings.blockchain_chain_id,
            "status": activity.status,
            "authorization_id": authority["authorization_id"],
            "network_calls_made": False,
        }

    async def activities(self) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(CryptoActivity))
        return [
            {
                "id": str(row.id),
                "blockchain": row.blockchain,
                "asset": row.asset,
                "amount": float(row.amount) if row.amount is not None else None,
                "address": row.address,
                "tx_hash": row.tx_hash,
                "status": row.status,
            }
            for row in result.scalars().all()
        ]
