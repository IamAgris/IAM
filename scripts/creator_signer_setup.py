"""Create a local Ed25519 Creator signer keypair for development (OD-18/OD-19).

The private key is written with 0600 permissions to a path outside the repo and
is never printed. Only the public key is printed for CREATOR_PUBLIC_KEY. For
production, replace this with a hardware signer/HSM and its public key.

Usage:
    python scripts/creator_signer_setup.py [--out-dir PATH] [--force]
"""

from __future__ import annotations

import argparse
import base64
import os
import stat
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=str(Path.home() / ".config" / "iam"),
        help="directory for the private key (default: ~/.config/iam)",
    )
    parser.add_argument("--force", action="store_true", help="overwrite an existing key")
    args = parser.parse_args()

    directory = Path(args.out_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    key_path = directory / "creator_ed25519.pem"
    if key_path.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing key: {key_path}")

    private_key = Ed25519PrivateKey.generate()
    payload = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(key_path, flags, stat.S_IRUSR | stat.S_IWUSR)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)

    public = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    print(f"signer_key_file={key_path}")
    print("CREATOR_PUBLIC_KEY=" + base64.b64encode(public).decode("ascii"))
    print("Never commit or log the private key. Keep it on the Creator machine.")


if __name__ == "__main__":
    main()
