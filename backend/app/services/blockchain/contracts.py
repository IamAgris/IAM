"""Smart-contract research, analysis and deployment preparation (proposed Doc 33).

Analysis is static and local. Generated templates are educational skeletons, never
production-ready contracts. Deployment and verification require signed Creator
approval and happen outside this module.
"""

from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.blockchain.providers.base import ProviderDenied, require_flag

STANDARDS = ("ERC-20", "ERC-721", "ERC-1155", "ERC-4337", "ERC-2612", "ERC-4626")

_DANGEROUS = ("selfdestruct", "delegatecall", "tx.origin", "suicide")
_OWNER_FUNCS = ("onlyOwner", "owner", "transferOwnership", "renounceOwnership")
_UNLIMITED = ("approve", "setApprovalForAll")


class ContractIntelligenceService:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_contract_dev_enabled,
            "auto_deploy_production": False,
            "testnet_only_in_sandbox": True,
            "templates_are_not_production_ready": True,
            "standards": list(STANDARDS),
        }

    def analyze(
        self,
        *,
        abi: Optional[List[Dict[str, Any]]] = None,
        source: str = "",
        is_proxy: bool = False,
        verified_source: bool = False,
    ) -> Dict[str, Any]:
        require_flag(settings.web3_contract_dev_enabled, "contract development is disabled")
        abi = abi or []
        names = {str(item.get("name", "")) for item in abi if isinstance(item, dict)}
        flags: List[str] = []
        for token in _DANGEROUS:
            if token in source:
                flags.append(f"dangerous_construct:{token}")
        for token in _OWNER_FUNCS:
            if token in source or token in names:
                flags.append(f"privileged_function:{token}")
        if any(name in names for name in _UNLIMITED):
            flags.append("approval_function_present")
        if is_proxy:
            flags.append("proxy_contract")
        if not verified_source:
            flags.append("unverified_source")

        detected = []
        if {"transfer", "balanceOf", "allowance"} <= names:
            detected.append("ERC-20")
        if {"ownerOf", "safeTransferFrom", "tokenURI"} & names:
            detected.append("ERC-721")
        if {"safeBatchTransferFrom", "balanceOfBatch"} & names:
            detected.append("ERC-1155")
        if {"deposit", "withdraw", "previewMint"} & names:
            detected.append("ERC-4626")
        if "permit" in names:
            detected.append("ERC-2612")

        return {
            "detected_standards": detected,
            "risk_flags": flags,
            "verified_source": verified_source,
            "proxy": is_proxy,
            "recommendation": "review_required" if flags else "research_only",
            "note": "Static analysis is indicative; an audit is required before production.",
        }

    @staticmethod
    def template(standard: str) -> str:
        if standard not in STANDARDS:
            raise ProviderDenied(f"unsupported standard '{standard}'")
        return (
            f"// {standard} educational skeleton — NOT production ready.\n"
            "// Requires OpenZeppelin imports, tests, audit and Creator approval before deployment.\n"
            "pragma solidity ^0.8.20;\n"
            "contract IAM" + standard.replace("-", "") + " {\n"
            "    // Implement the standard interface with audited, pinned dependencies.\n"
            "}\n"
        )

    def prepare_deployment(
        self, *, standard: str, chain_id: str, testnet: bool = True
    ) -> Dict[str, Any]:
        require_flag(settings.web3_contract_dev_enabled, "contract development is disabled")
        if standard not in STANDARDS:
            raise ProviderDenied(f"unsupported standard '{standard}'")
        if not testnet:
            raise ProviderDenied("production deployment requires a signed production gate")
        return {
            "status": "prepared",
            "standard": standard,
            "chain_id": chain_id,
            "testnet": True,
            "approval_action": "web3.contract.deploy_testnet" if chain_id in ("11155111", "84532") else None,
            "execution_enabled": False,
            "note": "Source review and tests must be recorded before deployment.",
        }

    def record_verification(
        self, *, address: str, chain_id: str, reference: str
    ) -> Dict[str, Any]:
        require_flag(settings.web3_contract_dev_enabled, "contract development is disabled")
        if not address or not reference:
            raise ProviderDenied("address and verification reference are required")
        return {
            "address": address,
            "chain_id": chain_id,
            "reference": reference,
            "verified": True,
            "note": "Reference recorded; corroborate with an independent explorer.",
        }
