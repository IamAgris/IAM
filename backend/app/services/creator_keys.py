"""Creator signing-key ceremony tooling.

The IAM backend NEVER holds the private key. This module provides:
  1. generate_keypair() — for the creator to generate an Ed25519 keypair offline
     (or in a secure environment they control).
  2. sign_challenge() — signs a challenge hash with a private key supplied by
     the creator's hardware signer / external signing tool. Used by the creator's
     signing tool, never by IAM's runtime.
  3. verify_signature() — public-key verification (mirrors creatorapproval_service).

Private key material is returned to the caller once and never persisted by IAM.
"""

import base64
import json
from typing import Dict, Any, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature


def generate_keypair() -> Dict[str, str]:
    """Generate a new Ed25519 keypair for the creator's hardware signer.

    Returns PEM private key (keep offline / in hardware) and public key to
    configure in IAM via CREATOR_PUBLIC_KEY.
    """
    private = Ed25519PrivateKey.generate()
    priv_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub_pem = private.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return {
        "private_key_pem": priv_pem,
        "public_key_pem": pub_pem,
        "public_key_base64": base64.b64encode(
            private.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode(),
        "warning": "Store the private key in hardware/offline. Never give it to IAM runtime.",
    }


def sign_challenge(private_key_pem: str, payload_hash: str, decision: str) -> str:
    """Sign '<payload_hash>|<decision>' — the exact bytes IAM verifies.

    Run this in the creator's signing tool, not in IAM's backend.
    """
    key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Creator key must be Ed25519")
    message = f"{payload_hash}|{decision}".encode("utf-8")
    return base64.b64encode(key.sign(message)).decode()


def verify_signature(public_key_pem_or_b64: str, payload_hash: str, decision: str, signature_b64: str) -> bool:
    """Public verification helper (mirrors the backend's authoritative check)."""
    try:
        if "-----BEGIN" in public_key_pem_or_b64:
            key = serialization.load_pem_public_key(public_key_pem_or_b64.encode())
        else:
            key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_pem_or_b64, validate=True))
        msg = f"{payload_hash}|{decision}".encode()
        key.verify(base64.b64decode(signature_b64, validate=True), msg)
        return True
    except (InvalidSignature, Exception):
        return False


def ceremony_steps() -> Dict[str, Any]:
    """Documented key-ceremony checklist for the creator."""
    return {
        "steps": [
            "1. Generate an Ed25519 keypair using generate_keypair() in an offline/secure environment.",
            "2. Store the private key in a hardware signer or offline vault — never in IAM runtime.",
            "3. Configure CREATOR_PUBLIC_KEY in IAM's environment with the public key.",
            "4. Set CREATOR_SIGNER_ID to the identity the signer will assert.",
            "5. When IAM emails an approval request, retrieve the challenge hash via the gateway.",
            "6. Sign '<hash>|<approved|rejected>' with the private key in your signer.",
            "7. Submit the signature through the protected creator gateway (HMAC-authenticated).",
            "8. IAM verifies the signature against the public key; a plain email reply is never authority.",
        ],
        "rule": "IAM never holds the private key. An ordinary email reply cannot authorize anything.",
    }
