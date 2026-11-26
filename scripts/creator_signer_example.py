"""Reference local Creator signer for the OD-42 signed-decision path.

Signs exactly ``<challenge_hash>|<approved|rejected>`` with an ED25519 private key
supplied in IAM_CREATOR_SIGNING_KEY (base64 raw 32-byte key or PEM). Prints a
base64 signature on stdout, which the Creator CLI submits to IAM.

The CLI passes the message as the final command-line argument, so this script
reads ``sys.argv[-1]``. It never contacts IAM and never stores a key.

For production, replace this example with a hardware signer / HSM command.
The key generated for the local smoke test is temporary and must be deleted
afterwards.
"""

import base64
import os
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def load_key() -> Ed25519PrivateKey:
    raw = os.environ.get("IAM_CREATOR_SIGNING_KEY", "").strip()
    if not raw:
        raise SystemExit("IAM_CREATOR_SIGNING_KEY is not set")
    if "-----BEGIN" in raw:
        key = serialization.load_pem_private_key(raw.encode("utf-8"), password=None)
    else:
        key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(raw, validate=True))
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("IAM_CREATOR_SIGNING_KEY must be an ED25519 private key")
    return key


def main() -> None:
    message = sys.argv[-1].encode("utf-8")
    signature = load_key().sign(message)
    print(base64.b64encode(signature).decode("ascii"))


if __name__ == "__main__":
    main()
