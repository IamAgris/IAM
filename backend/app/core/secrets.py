"""Secret sourcing and production policy enforcement.

Docker secrets are supported through ``<ENV_NAME>_FILE`` variables. Values are
never logged. In production, placeholder values are rejected at startup.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings
from app.services.crypto_service import CryptoService

PLACEHOLDERS = ("change-me", "change-this", "change-me-securely")


def read_secret(name: str) -> Optional[str]:
    """Return a secret from a Docker secret file or the environment."""
    file_var = f"{name}_FILE"
    path = os.environ.get(file_var)
    if path:
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except OSError:
            return None
    return os.environ.get(name)


def placeholder_secrets() -> List[str]:
    """Names whose values are missing or still contain placeholders."""
    candidates: Dict[str, Optional[str]] = {
        "APP_SECRET_KEY": settings.app_secret_key,
        "SESSION_SECRET": settings.session_secret,
        "POSTGRES_PASSWORD": settings.postgres_password,
        "LITELLM_MASTER_KEY": settings.litellm_master_key,
        "S3_SECRET_KEY": settings.s3_secret_key,
    }
    for name in list(candidates):
        file_value = read_secret(name)
        if file_value:
            candidates[name] = file_value

    bad: List[str] = [
        name
        for name, value in candidates.items()
        if not value or any(p in str(value).lower() for p in PLACEHOLDERS)
    ]
    if not CryptoService().key_is_secure:
        bad.append("ENCRYPTION_KEY")
    return bad


def web3_secret_gaps() -> List[str]:
    """Missing/invalid secrets for Web3 features that are actually enabled.

    Disabled features never block startup. Credentials are read from Docker
    secret files through ``read_secret``; values are never returned or logged.
    """
    required: List[str] = []
    if settings.thirdweb_read_enabled:
        required.extend(
            [settings.blockchain_client_id_env, settings.blockchain_secret_env]
        )
    if settings.bitcoin_core_read_enabled:
        required.append(settings.bitcoin_core_cookie_env)
    if settings.lnd_read_enabled:
        required.extend([settings.lnd_macaroon_env, settings.lnd_tls_cert_env])
    if settings.cln_read_enabled:
        required.extend([settings.cln_rune_env, settings.cln_ca_cert_env])
    if settings.web3_execution_enabled:
        required.append(settings.blockchain_secret_env)
    if settings.lnd_write_enabled:
        required.append(settings.lnd_write_macaroon_env)
    if settings.cln_write_enabled:
        required.append(settings.cln_write_rune_env)
    return sorted(
        name
        for name in required
        if not read_secret(name) or any(p in str(read_secret(name)).lower() for p in PLACEHOLDERS)
    )


def enforce_secret_policy() -> None:
    """Fail closed if a production deployment still uses placeholder secrets."""
    if settings.app_env.lower() != "production":
        return
    bad = placeholder_secrets() + web3_secret_gaps()
    if bad:
        raise RuntimeError(
            "Production startup blocked: replace placeholder secrets before running: "
            + ", ".join(sorted(set(bad)))
        )
