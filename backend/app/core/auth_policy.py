"""Path-to-scope policy for API authentication.

Public routes stay open (health, docs, global access, and the HMAC-protected
Creator gateway). Everything else requires a credential with at least the
scope listed here. Creator authority itself is still email + signed challenge;
an admin API key can call the Creator endpoints but cannot create authority.
"""

from typing import Optional

# Service credentials rank with operators so internal workers can call
# autonomy/research/etc., but remain a distinct identity in the audit trail.
SCOPE_RANK = {"user": 1, "service": 3, "operator": 3, "admin": 4}

PUBLIC_EXACT = {
    "/",
    "/health",
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",
    "/api/v1/auth/bootstrap",
    "/api/v1/creator/gateway/decision",  # protected by HMAC, not a bearer key
}

PUBLIC_PREFIXES = (
    "/api/v1/access",  # global/anonymous access
)

ADMIN_PREFIXES = (
    "/api/v1/skill-runtime",
    "/api/v1/skill-forge",
    "/api/v1/skillforge",  # legacy alias
    "/api/v1/cybersecurity",
    "/api/v1/creator",  # gateway exact path above is the exception
    "/api/v1/governance",
    "/api/v1/internet",
    "/api/v1/network",
    "/api/v1/external-presence",
    "/api/v1/resilience",
    "/api/v1/auth",
    "/api/v1/setup",
    # Node registration/attestation use operator credentials; revocation is
    # checked explicitly in the route handler (creator admin scope).
    "/api/v1/development",
    "/api/v1/economics",
    "/api/v1/finance",
)

USER_PREFIXES = (
    "/api/v1/interface",
    "/api/v1/conversations",
    "/api/v1/memory",
    "/api/v1/languages",
    "/api/v1/skills",
    "/api/v1/identity",
)


def normalize_path(path: str) -> str:
    if len(path) > 1 and path.endswith("/"):
        return path.rstrip("/")
    return path


def required_scope(path: str) -> Optional[str]:
    """Return the minimum scope for a path, or None for public routes."""
    path = normalize_path(path)
    if path in PUBLIC_EXACT or path.startswith(PUBLIC_PREFIXES):
        return None
    if path.startswith(ADMIN_PREFIXES):
        return "admin"
    if path.startswith(USER_PREFIXES):
        return "user"
    return "operator"


def has_scope(actual: str, required: str) -> bool:
    return SCOPE_RANK.get(actual, 0) >= SCOPE_RANK.get(required, 99)
