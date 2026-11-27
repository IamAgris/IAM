"""Preflight for Creator approval by SMTP on a private domain.

Checks configuration without printing secret values. This does not send email
and does not grant authority — it only confirms that the carrier is ready.
"""

import os
import sys
from typing import List


def check() -> List[str]:
    """Return configuration failures; never include secret values."""
    address = os.environ.get("CREATOR_EMAIL", "").strip()
    domain = os.environ.get("CREATOR_EMAIL_DOMAIN", "").strip().lower()
    transport = os.environ.get("CREATOR_EMAIL_TRANSPORT", "log").strip().lower()
    host = os.environ.get("CREATOR_SMTP_HOST", "").strip()
    user = os.environ.get("CREATOR_SMTP_USER", "").strip()
    password = os.environ.get("CREATOR_SMTP_PASSWORD", "").strip()
    public_key = os.environ.get("CREATOR_PUBLIC_KEY", "").strip()
    gateway = os.environ.get("CREATOR_GATEWAY_SECRET", "").strip()
    failures: List[str] = []
    if not address or "@" not in address:
        failures.append("CREATOR_EMAIL must be a full address")
    else:
        actual = address.rsplit("@", 1)[1].lower()
        if domain and actual != domain and not actual.endswith("." + domain):
            failures.append("CREATOR_EMAIL is outside CREATOR_EMAIL_DOMAIN")
        if actual in {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com"}:
            failures.append("use the private domain, not a public mailbox")
    if transport != "smtp":
        failures.append("CREATOR_EMAIL_TRANSPORT must be 'smtp'")
    if not host:
        failures.append("CREATOR_SMTP_HOST is required")
    if not user:
        failures.append("CREATOR_SMTP_USER is required")
    if not password:
        failures.append("CREATOR_SMTP_PASSWORD is required")
    if not public_key:
        failures.append("CREATOR_PUBLIC_KEY is required for signature verification")
    if not gateway:
        failures.append("CREATOR_GATEWAY_SECRET is required to receive signed decisions")
    return failures


def main() -> int:
    address = os.environ.get("CREATOR_EMAIL", "").strip()
    domain = os.environ.get("CREATOR_EMAIL_DOMAIN", "").strip().lower()
    transport = os.environ.get("CREATOR_EMAIL_TRANSPORT", "log").strip().lower()
    host = os.environ.get("CREATOR_SMTP_HOST", "").strip()
    user = os.environ.get("CREATOR_SMTP_USER", "").strip()
    password = os.environ.get("CREATOR_SMTP_PASSWORD", "").strip()
    public_key = os.environ.get("CREATOR_PUBLIC_KEY", "").strip()
    gateway = os.environ.get("CREATOR_GATEWAY_SECRET", "").strip()

    failures = check()

    print(f"creator_email_domain: {domain or '<unset>'}")
    print(f"transport: {transport}")
    print(f"smtp_host: {host or '<unset>'}")
    print(f"smtp_user: {user or '<unset>'}")
    print(f"public_key_configured: {bool(public_key)}")
    print(f"gateway_configured: {bool(gateway)}")
    if failures:
        for item in failures:
            print(f"FAIL {item}", file=sys.stderr)
        return 1
    print("PREFLIGHT OK — SMTP private-domain carrier is configured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
