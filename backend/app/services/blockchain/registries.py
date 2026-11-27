"""Contract, token and provider-health registries (proposed Doc 33).

IAM owns these records so they survive provider replacement. All entries are
unverified until an operator reviews them; no registry entry grants authority.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.web3 import Web3Asset, Web3Contract, Web3ProviderHealth
from app.services.blockchain.providers.base import ProviderDenied, require_flag


class ContractRegistryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self,
        *,
        chain_id: str,
        address: str,
        standard: Optional[str] = None,
        source_verified: bool = False,
        proxy_detected: bool = False,
        risk_flags: Optional[List[str]] = None,
        actor: str = "iam",
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if not chain_id or not address:
            raise ProviderDenied("chain_id and address are required")
        rows = (await self.db.execute(select(Web3Contract))).scalars().all()
        if any(row.chain_id == chain_id and row.address == address for row in rows):
            raise ProviderDenied("contract already registered")
        row = Web3Contract(
            chain_id=chain_id,
            address=address,
            standard=standard,
            source_verified=source_verified,
            proxy_detected=proxy_detected,
            risk_flags=list(risk_flags or []),
        )
        self.db.add(row)
        await self.db.commit()
        return {"id": str(row.id), "chain_id": chain_id, "address": address, "verified": source_verified}

    async def list(self, chain_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = (await self.db.execute(select(Web3Contract))).scalars().all()
        return [
            {
                "chain_id": row.chain_id,
                "address": row.address,
                "standard": row.standard,
                "source_verified": row.source_verified,
                "proxy_detected": row.proxy_detected,
                "risk_flags": row.risk_flags,
            }
            for row in rows
            if not chain_id or row.chain_id == chain_id
        ]


class TokenRegistryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self,
        *,
        chain_id: str,
        symbol: str,
        contract_address: Optional[str] = None,
        decimals: Optional[int] = None,
        asset_type: str = "fungible",
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if asset_type not in ("native", "fungible", "nft", "multi_token", "vault_share"):
            raise ProviderDenied("unsupported asset type")
        row = Web3Asset(
            chain_id=chain_id,
            contract_address=contract_address,
            symbol=symbol,
            decimals=decimals,
            asset_type=asset_type,
            risk_flags=[],
        )
        self.db.add(row)
        await self.db.commit()
        return {"chain_id": chain_id, "symbol": symbol, "asset_type": asset_type}

    async def list(self, chain_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = (await self.db.execute(select(Web3Asset))).scalars().all()
        return [
            {
                "chain_id": row.chain_id,
                "symbol": row.symbol,
                "contract_address": row.contract_address,
                "asset_type": row.asset_type,
                "risk_flags": row.risk_flags,
            }
            for row in rows
            if not chain_id or row.chain_id == chain_id
        ]


class ProviderHealthRegistry:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def record(
        self, *, provider: str, network: Optional[str], available: bool, latency_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        rows = (await self.db.execute(select(Web3ProviderHealth))).scalars().all()
        entry = next(
            (row for row in rows if row.provider == provider and row.network == network), None
        )
        if entry:
            entry.available = available  # type: ignore[assignment]
            entry.latency_ms = latency_ms  # type: ignore[assignment]
        else:
            entry = Web3ProviderHealth(
                provider=provider, network=network, available=available, latency_ms=latency_ms
            )
            self.db.add(entry)
        await self.db.commit()
        return {"provider": provider, "network": network, "available": available}

    async def list(self) -> List[Dict[str, Any]]:
        rows = (await self.db.execute(select(Web3ProviderHealth))).scalars().all()
        return [
            {"provider": r.provider, "network": r.network, "available": r.available}
            for r in rows
        ]
