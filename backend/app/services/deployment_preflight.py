"""Deployment preflight — validates configuration without exposing secrets.

This reports names and status only. It never returns secret values. All checks
are fail-closed: missing configuration is reported as a blocker, not assumed.
"""

import base64
import os
from typing import Any, Dict, List

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.core.config import settings
from app.services.cybersecurity.security_guard import (
    SecurityGuard,
    SecurityGuardDenied,
)
from app.core.infisical import get_infisical_client
from app.core.secrets import placeholder_secrets
from app.services.blockchain.activation import check_web3_activation
from app.services.crypto_service import CryptoService


def _public_key_valid(raw: str) -> bool:
    if not raw:
        return False
    try:
        if "-----BEGIN" in raw:
            key = serialization.load_pem_public_key(raw.encode("utf-8"))
        else:
            key = Ed25519PublicKey.from_public_bytes(base64.b64decode(raw, validate=True))
        return isinstance(key, Ed25519PublicKey)
    except Exception:
        return False


def check_deployment() -> Dict[str, Any]:
    """Return a redacted readiness report for the current environment."""
    checks: List[Dict[str, str]] = []

    def add(name: str, ok: bool, detail: str, blocking: bool = True) -> None:
        checks.append(
            {
                "name": name,
                "status": "ok" if ok else ("blocker" if blocking else "warning"),
                "detail": detail,
            }
        )

    # Creator email approval path (OD-18/OD-19)
    add(
        "creator_email",
        bool(settings.creator_email),
        "CREATOR_EMAIL must be the verified Creator address",
    )
    add(
        "creator_public_key",
        _public_key_valid(settings.creator_public_key),  # type: ignore[arg-type]
        "CREATOR_PUBLIC_KEY must be a valid ED25519 public key",
    )
    add(
        "creator_gateway_secret",
        bool(settings.creator_gateway_secret),
        "CREATOR_GATEWAY_SECRET must be set; an empty value disables the gateway",
    )

    transport = (settings.creator_email_transport or "log").lower()
    if transport == "log":
        add(
            "creator_email_transport",
            True,
            "log transport active — email packages are recorded, nothing is sent",
            blocking=False,
        )
    elif transport == "smtp":
        add(
            "creator_smtp_host",
            bool(settings.creator_smtp_host),
            "CREATOR_SMTP_HOST required for smtp transport",
        )
        add(
            "creator_email_from",
            bool(settings.creator_email_from),
            "CREATOR_EMAIL_FROM required for smtp transport",
        )
        add(
            "creator_smtp_password",
            bool(os.environ.get(settings.creator_smtp_password_env, "")),
            f"{settings.creator_smtp_password_env} must contain the SMTP password",
        )
    elif transport == "http":
        add(
            "creator_email_http_url",
            bool(settings.creator_email_http_url),
            "CREATOR_EMAIL_HTTP_URL required for http transport",
        )
    else:
        add(
            "creator_email_transport",
            False,
            f"unknown transport: {transport}",
        )

    # Secret management and encryption at rest
    encryption_secure = CryptoService().key_is_secure
    add(
        "encryption_key",
        encryption_secure,
        "ENCRYPTION_KEY must be a real base64 32-byte key for production",
        blocking=settings.app_env.lower() == "production",
    )
    bad_secrets = placeholder_secrets()
    add(
        "secret_policy",
        not bad_secrets,
        (
            "replace placeholder secrets: " + ", ".join(sorted(bad_secrets))
            if bad_secrets
            else "no placeholder secrets detected"
        ),
        blocking=settings.app_env.lower() == "production",
    )

    # Optional Infisical Cloud source (OD-58). Redacted: names/status only.
    backend = settings.secrets_backend.lower()
    add(
        "secrets_backend",
        backend in {"docker", "infisical"},
        "SECRETS_BACKEND must be docker or infisical",
    )
    if backend == "infisical":
        client = get_infisical_client()
        add(
            "infisical_host",
            client.host_allowed(),
            "INFISICAL_SITE_URL must be an HTTPS allowlisted Infisical host",
        )
        add(
            "infisical_credentials",
            client.has_credentials(),
            f"{settings.infisical_client_id_env} and "
            f"{settings.infisical_client_secret_env} must be Docker secrets",
        )
        add(
            "infisical_project",
            bool(settings.infisical_project_id),
            "INFISICAL_PROJECT_ID is required when the Infisical backend is enabled",
        )
        client.refresh()
        reachable = bool(client.status()["reachable"])
        add(
            "infisical_reachability",
            reachable,
            (
                "Infisical secrets fetched; Docker secrets remain the fallback"
                if reachable
                else "Infisical fetch failed; Docker secrets remain the fallback"
            ),
            blocking=False,
        )

    # API credentials
    add(
        "bootstrap_key",
        bool(os.environ.get(settings.auth_bootstrap_key_env, "")),
        f"{settings.auth_bootstrap_key_env} is needed to create the first credential",
        blocking=False,
    )

    # Skill Runtime
    runtime_adapter = (settings.skill_runtime_adapter or "stub").lower()
    add(
        "skill_runtime_adapter",
        runtime_adapter in {"stub", "docker"},
        "SKILL_RUNTIME_ADAPTER must be stub or docker",
    )
    if settings.skill_runtime_enabled and runtime_adapter == "docker":
        add(
            "skill_runtime_image",
            bool(settings.skill_runtime_image),
            "SKILL_RUNTIME_IMAGE required when the Docker adapter is enabled",
        )

    # External security engine (optional)
    if settings.artex_enabled:
        try:
            SecurityGuard().validate_base_url(
                settings.artex_base_url, allow_private_network=False
            )
            endpoint_ok = True
        except SecurityGuardDenied:
            endpoint_ok = False
        add(
            "artex_endpoint",
            endpoint_ok,
            "ARTEX base URL must be loopback unless explicitly opted into private networking",
        )
        add(
            "artex_token",
            bool(os.environ.get(settings.artex_token_env, "")),
            f"{settings.artex_token_env} must contain the MCP bearer token",
        )
        if not settings.artex_dry_run:
            add(
                "artex_dry_run",
                False,
                "ARTEX dry-run is disabled — real tasks may be started",
                blocking=False,
            )
    else:
        add(
            "artex",
            True,
            "external security engine disabled",
            blocking=False,
        )

    # Proposed Doc 35 activation gate — redacted, fail-closed, no secret values.
    checks.extend(check_web3_activation()["checks"])

    blockers = [c["name"] for c in checks if c["status"] == "blocker"]
    warnings = [c["name"] for c in checks if c["status"] == "warning"]
    return {
        "ready": not blockers,
        "checks": checks,
        "blockers": blockers,
        "warnings": warnings,
        "note": "Secrets are never included in this report.",
    }
