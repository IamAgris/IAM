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
    "/health/live",
    "/health/ready",
    "/metrics",
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",
    "/api/v1/auth/bootstrap",
    "/api/v1/creator/gateway/decision",  # protected by HMAC, not a bearer key
    "/api/v1/autonomy/status",  # read-only worker status (operational visibility)
}

PUBLIC_PREFIXES = (
    "/api/v1/access",     # global/anonymous access
    "/api/v1/models",     # public chat proxy — gateway key stays backend-only
    "/api/v1/interface",  # public display: suggestions + permission-filtered nodes
)

ADMIN_PREFIXES = (
    "/api/v1/skill-runtime",
    "/api/v1/deployment",
    "/api/v1/skill-forge",
    "/api/v1/skillforge",  # legacy alias
    "/api/v1/cybersecurity",
    "/api/v1/creator",  # gateway exact path above is the exception
    "/api/v1/governance",
    "/api/v1/internet",
    "/api/v1/browser",  # Doc 29: browser operations are admin-gated
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
    "/api/v1/free-sandboxes",
    "/api/v1/workspaces",
    "/api/v1/aegis",
    "/api/v1/irwm",
    "/api/v1/model-independence",
    "/api/v1/blockchain",
    "/api/v1/web3",       # proposed Doc 30: registries, prepare-only transactions
    "/api/v1/nodes",      # proposed Doc 30: read-only Bitcoin/LND/CLN nodes
    "/api/v1/banking",
    "/api/v1/trading",
    "/api/v1/prediction-markets",
    "/api/v1/gaming-intelligence",
    "/api/v1/investment-intelligence",
    "/api/v1/provider-registry",
    "/api/v1/digital-assets",
    "/api/v1/domain-registrations",
    "/api/v1/social",
    "/api/v1/assistance",
    "/api/v1/uwaie/computer",
    "/api/v1/mobile",
    "/api/v1/credentials",
    "/api/v1/mfa",
    # P2P HTTP endpoints move/store messages: credential required. The
    # WebSocket upgrade authenticates separately with its per-peer secret.
    "/api/v1/p2p",
)

USER_PREFIXES = (
    "/api/v1/interface",
    "/api/v1/capabilities",
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
