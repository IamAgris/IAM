"""Creator key ceremony routes — key generation and offline signing helpers.

These are utilities for the CREATOR's signing environment. IAM runtime never
holds a private key. Routes are gated by operator/admin auth.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.creator_keys import generate_keypair, ceremony_steps, verify_signature

router = APIRouter(prefix="/api/v1/creator/keys", tags=["creator-keys"])


class SignRequest(BaseModel):
    private_key_pem: str
    payload_hash: str
    decision: str


class VerifyRequest(BaseModel):
    public_key: str
    payload_hash: str
    decision: str
    signature: str


@router.post("/generate")
async def generate():
    """Generate a new creator Ed25519 keypair (keep private key offline)."""
    return generate_keypair()


@router.get("/ceremony")
async def ceremony():
    """The documented creator key-ceremony checklist."""
    return ceremony_steps()


@router.post("/sign")
async def sign(request: SignRequest):
    """Sign a challenge with a creator-supplied private key (external signer use)."""
    from app.services.creator_keys import sign_challenge
    try:
        return {"signature": sign_challenge(request.private_key_pem, request.payload_hash, request.decision)}
    except Exception as e:
        return {"error": str(e)}


@router.post("/verify")
async def verify(request: VerifyRequest):
    """Verify a challenge signature against a public key."""
    return {"valid": verify_signature(request.public_key, request.payload_hash, request.decision, request.signature)}
