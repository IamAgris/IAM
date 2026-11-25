"""Inbound gateway authentication for Creator decisions.

The ED25519 signature over the challenge is the authority proof. The HMAC here
is a second, independent check that the callback actually came from the
configured email/signer gateway, so arbitrary callers cannot spam the decide
endpoint. An empty secret disables the gateway entirely.
"""

import hashlib
import hmac
from typing import Literal, Optional

from pydantic import BaseModel

CREATOR_SIGNATURE_HEADER = "X-Creator-Signature"


class DecisionGatewayRequest(BaseModel):
    request_id: str
    decision: Literal["approved", "rejected"]
    signature: str
    signer_id: str
    message_id: Optional[str] = None


def verify_gateway_signature(raw_body: bytes, provided: str, secret: str) -> bool:
    """Constant-time HMAC-SHA256 over the exact raw request body."""
    if not secret or not provided:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided)
