"""Wallet and address registry (proposed Doc 35 §8.1) — metadata only.

No key, seed phrase, derivation secret, macaroon or rune is accepted or stored.
An address is a routing destination, never an identity (OD-01) or an authority.
States move forward only: proposed → verified → active → suspended → retired.
"""

import os
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.web3 import Web3Wallet
from app.services.blockchain.audit import BlockchainAuditService
from app.services.blockchain.providers.base import ProviderDenied, require_flag

DOMAINS = ("operational", "treasury", "project", "development", "user")
TRANSITIONS = {
    "proposed": ("verified", "retired"),
    "verified": ("active", "suspended", "retired"),
    "active": ("suspended", "retired"),
    "suspended": ("active", "retired"),
    "retired": (),
}
_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _wallet_ulid() -> str:
    alphabet = _ULID_ALPHABET
    stamp = int(time.time() * 1000)
    time_part = ""
    for _ in range(10):
        time_part = alphabet[stamp % 32] + time_part
        stamp //= 32
    random_part = "".join(alphabet[b % 32] for b in os.urandom(16))
    return time_part + random_part


class WalletRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_registry_enabled,
            "domains": list(DOMAINS),
            "transitions": {key: list(value) for key, value in TRANSITIONS.items()},
            "stores_key_material": False,
            "address_is_identity": False,
            "address_grants_authority": False,
        }

    async def _audit(self, event: str, actor: str, target: str, details: Dict[str, Any]) -> None:
        if settings.web3_audit_enabled:
            await BlockchainAuditService(self.db).append(
                event_type=event, actor=actor, target=target, details=details
            )

    async def register(
        self,
        *,
        domain: str,
        provider: str,
        address: str,
        network_id: Optional[str] = None,
        verification_method: Optional[str] = None,
        verification_evidence_ref: Optional[str] = None,
        policy_ref: Optional[str] = None,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if domain not in DOMAINS:
            raise ProviderDenied(f"unknown wallet domain '{domain}'")
        if not provider or not address or not isinstance(address, str):
            raise ProviderDenied("provider and address are required")
        wallet_id = _wallet_ulid()
        row = Web3Wallet(
            wallet_id=wallet_id,
            domain=domain,
            provider=provider,
            network_id=network_id,
            address=address,
            state="proposed",
            verification_method=verification_method,
            verification_evidence_ref=verification_evidence_ref,
            policy_ref=policy_ref,
        )
        self.db.add(row)
        await self.db.flush()
        await self._audit(
            "web3_wallet_registered", actor, wallet_id,
            {"domain": domain, "provider": provider, "state": "proposed"},
        )
        await self.db.commit()
        return {"wallet_id": wallet_id, "domain": domain, "state": "proposed", "address": address}

    async def _get(self, wallet_id: str) -> Web3Wallet:
        result = await self.db.execute(select(Web3Wallet))
        row = next((item for item in result.scalars().all() if item.wallet_id == wallet_id), None)
        if not row:
            raise LookupError("wallet not found")
        return row

    async def transition(
        self,
        *,
        wallet_id: str,
        target: str,
        actor: str = "iam",
        verification_method: Optional[str] = None,
        verification_evidence_ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        row = await self._get(wallet_id)
        if target not in TRANSITIONS.get(str(row.state), ()):
            raise ProviderDenied(
                f"transition {row.state} → {target} is not allowed"
            )
        if target == "verified" and not (verification_method and verification_evidence_ref):
            raise ProviderDenied(
                "verification requires a method and an evidence reference"
            )
        previous = row.state
        row.state = target  # type: ignore[assignment]
        if verification_method:
            row.verification_method = verification_method  # type: ignore[assignment]
        if verification_evidence_ref:
            row.verification_evidence_ref = verification_evidence_ref  # type: ignore[assignment]
        await self.db.flush()
        await self._audit(
            "web3_wallet_state_changed", actor, wallet_id,
            {"from": previous, "to": target},
        )
        await self.db.commit()
        return {"wallet_id": wallet_id, "state": target, "previous": previous}

    async def list_wallets(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        result = await self.db.execute(select(Web3Wallet))
        return [
            {
                "wallet_id": row.wallet_id,
                "domain": row.domain,
                "provider": row.provider,
                "address": row.address,
                "state": row.state,
                "verification_method": row.verification_method,
            }
            for row in result.scalars().all()
            if not domain or row.domain == domain
        ]
