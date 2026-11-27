"""NFT and digital-asset preparation (proposed Doc 35).

No mint, listing, purchase or transfer is executed. Metadata references are
content-addressed identifiers, not file contents; no IPFS provider is assumed.
"""

from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag


class DigitalAssetService:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_nft_enabled,
            "execution_enabled": False,
            "standards": ("ERC-721", "ERC-1155"),
            "storage": "provider-independent content references",
        }

    @staticmethod
    def validate_metadata_ref(ref: str) -> Dict[str, Any]:
        value = (ref or "").strip()
        if value.startswith("ipfs://") and len(value) > 7:
            return {"scheme": "ipfs", "reference": value, "valid": True}
        if value.startswith(("https://", "http://")):
            return {"scheme": "http", "reference": value, "valid": True}
        return {"scheme": None, "reference": value, "valid": False}

    def prepare_mint(
        self,
        *,
        chain_id: str,
        standard: str,
        owner: str,
        metadata_ref: str,
        royalty_bps: int = 0,
    ) -> Dict[str, Any]:
        require_flag(settings.web3_nft_enabled, "NFT capability is disabled")
        if standard not in ("ERC-721", "ERC-1155"):
            raise ProviderDenied("standard must be ERC-721 or ERC-1155")
        if not owner:
            raise ProviderDenied("owner address is required")
        metadata = self.validate_metadata_ref(metadata_ref)
        if not metadata["valid"]:
            raise ProviderDenied("a valid ipfs:// or http(s) metadata reference is required")
        if not 0 <= royalty_bps <= 10000:
            raise ProviderDenied("royalty_bps must be between 0 and 10000")
        return {
            "status": "prepared",
            "chain_id": chain_id,
            "standard": standard,
            "owner": owner,
            "metadata": metadata,
            "royalty_bps": royalty_bps,
            "approval_action": "web3.nft.mint",
            "approval_required": True,
            "execution_enabled": False,
        }

    def prepare_listing(
        self, *, chain_id: str, contract: str, token_id: str, price: float, marketplace: str
    ) -> Dict[str, Any]:
        require_flag(settings.web3_nft_enabled, "NFT capability is disabled")
        if not contract or not token_id or not marketplace:
            raise ProviderDenied("contract, token_id and marketplace are required")
        if price <= 0:
            raise ProviderDenied("price must be positive")
        return {
            "status": "prepared",
            "chain_id": chain_id,
            "contract": contract,
            "token_id": token_id,
            "price": price,
            "marketplace": marketplace,
            "approval_action": "web3.nft.list",
            "approval_required": True,
            "execution_enabled": False,
        }

    def verify_ownership(
        self, *, owner: str, contract: str, token_id: str, evidence_ref: Optional[str] = None
    ) -> Dict[str, Any]:
        require_flag(settings.web3_nft_enabled, "NFT capability is disabled")
        if not all((owner, contract, token_id)):
            raise ProviderDenied("owner, contract and token_id are required")
        return {
            "owner": owner,
            "contract": contract,
            "token_id": token_id,
            "evidence_ref": evidence_ref,
            "verification": "reference_recorded",
            "note": "Corroborate with an independent ownerOf/read call before relying on it.",
        }
