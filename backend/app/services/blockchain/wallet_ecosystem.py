"""Extended wallet ecosystem: SIWE verification, multisig, session keys, backups.

SIWE verification is real: EIP-191 prefixed message → Keccak-256 → secp256k1
recovery via the installed ``cryptography`` library. No private key is held.
Records are metadata only.
"""

import re
from typing import Any, Dict

from app.core.config import settings
from app.services.blockchain.keccak import keccak256
from app.services.blockchain.providers.base import ProviderDenied, require_flag
from app.services.blockchain import secp256k1

_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_HEX_SIG_RE = re.compile(r"^[0-9a-fA-F]{130}$")


def eip191_digest(message: str) -> bytes:
    raw = message.encode("utf-8")
    return keccak256(b"\x19Ethereum Signed Message:\n" + str(len(raw)).encode() + raw)


def address_from_public_key(public_key: tuple[int, int]) -> str:
    return "0x" + keccak256(secp256k1.public_key_bytes(public_key)[1:])[-20:].hex()


class WalletEcosystemService:
    def policy(self) -> Dict[str, Any]:
        return {
            "enabled": settings.web3_registry_enabled,
            "siwe_real_verification": True,
            "address_is_identity": False,
            "stores_private_keys": False,
            "multisig_required_for_treasury": True,
        }

    def verify_siwe(
        self, *, message: str, signature_hex: str, claimed_address: str
    ) -> Dict[str, Any]:
        """Verify an EIP-191/SIWE signature. Rejects malformed input fail-closed."""
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if not message or not _HEX_SIG_RE.match(signature_hex or ""):
            raise ProviderDenied("message and a 65-byte hex signature are required")
        if not _ADDRESS_RE.match(claimed_address or ""):
            raise ProviderDenied("claimed_address must be a 20-byte hex address")
        raw = bytes.fromhex(signature_hex)
        r = int.from_bytes(raw[:32], "big")
        s = int.from_bytes(raw[32:64], "big")
        recovery = raw[64]
        if recovery in (27, 28):
            recovery -= 27
        if recovery not in (0, 1) or r == 0 or s == 0:
            raise ProviderDenied("invalid signature recovery id or components")
        digest = eip191_digest(message)
        public_key = secp256k1.recover_public_key(r, s, recovery, digest)
        matched = bool(
            public_key
            and secp256k1.verify(public_key, r, s, digest)
            and address_from_public_key(public_key).lower() == claimed_address.lower()
        )
        recovered = address_from_public_key(public_key) if public_key else None
        nonce_match = re.search(r"(?im)^Nonce:\s*(\S+)", message)
        chain_match = re.search(r"(?im)^Chain ID:\s*(\d+)", message)
        return {
            "verified": matched,
            "recovered_address": recovered,
            "claimed_address": claimed_address,
            "nonce": nonce_match.group(1) if nonce_match else None,
            "chain_id": chain_match.group(1) if chain_match else None,
            "note": "A verified wallet signature authenticates wallet control, not IAM identity authority.",
        }

    def session_key(
        self, *, wallet_id: str, methods: list[str], expiry: str, spend_cap: float
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if not wallet_id or not methods or spend_cap <= 0:
            raise ProviderDenied("wallet_id, methods and a positive spend_cap are required")
        return {
            "status": "prepared",
            "wallet_id": wallet_id,
            "methods": list(methods),
            "expiry": expiry,
            "spend_cap": spend_cap,
            "can_create_session_keys": False,
            "approval_required": True,
            "execution_enabled": False,
        }

    def multisig(self, *, wallet_id: str, signers: list[str], threshold: int) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if len(set(signers)) < 2 or not 1 <= threshold <= len(set(signers)):
            raise ProviderDenied("at least two distinct signers and a valid threshold are required")
        return {
            "status": "prepared",
            "wallet_id": wallet_id,
            "signers": list(dict.fromkeys(signers)),
            "threshold": threshold,
            "change_requires_creator_approval": True,
            "execution_enabled": False,
        }

    def backup_reference(self, *, wallet_id: str, method: str, reference: str) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if not method or not reference:
            raise ProviderDenied("method and reference are required")
        return {
            "wallet_id": wallet_id,
            "method": method,
            "reference": reference,
            "stores_secret_material": False,
            "note": "A database backup is not a Lightning channel backup.",
        }

    def prepare_transfer(
        self, *, wallet_id: str, to_address: str, amount: float, chain_id: str
    ) -> Dict[str, Any]:
        require_flag(settings.web3_registry_enabled, "Web3 registry is disabled")
        if not _ADDRESS_RE.match(to_address or "") or amount <= 0:
            raise ProviderDenied("a valid address and positive amount are required")
        return {
            "status": "prepared",
            "wallet_id": wallet_id,
            "to_address": to_address,
            "amount": amount,
            "chain_id": chain_id,
            "approval_action": "web3.transaction.broadcast",
            "approval_required": True,
            "execution_enabled": False,
        }
