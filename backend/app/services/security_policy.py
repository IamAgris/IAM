"""Canonical white-hat enforcement policy (WH-01 / WH-02).

The enforcement lives here, outside the personality prompt. A target may be
used only when an active, unrevoked, unexpired signed Creator authorization
covers it and permits the requested operation. Offensive capabilities are
denied by taxonomy, regardless of how a request is worded.

The authority records are the existing ``creator_authorizations`` rows; no new
authority path or database table is introduced.
"""

import ipaddress
import re
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creatorapproval import CreatorAuthorization
from app.services.creatorapproval_service import CreatorApprovalService

AUTHORIZATION_ACTION = "security.authorised_target"

# WH-02 taxonomy: capabilities IAM does not execute, even when studying them.
FORBIDDEN_CAPABILITIES = frozenset(
    {
        "exploitation",
        "exploit",
        "credential theft",
        "persistence",
        "persist",
        "evasion",
        "evade",
        "internet-wide",
        "intrusion",
        "exfiltration",
        "destructive",
        "implant",
        "command and control",
        "phishing",
        "privilege escalation",
        "bypass",
        "reverse shell",
        "ransom",
        "ddos",
        "mass scan",
        "wipe",
        "unauthorised",
        "unauthorized",
        "crime",
    }
)

_TERMS = sorted(
    (re.escape(term).replace(r"\ ", r"[\s_-]") for term in FORBIDDEN_CAPABILITIES),
    key=len,
    reverse=True,
)
FORBIDDEN_OPERATION_PATTERN = re.compile(r"(?i)(?:" + "|".join(_TERMS) + r")")


class AuthorisedTargetDenied(PermissionError):
    """Raised when a target/operation is outside signed, active authority."""


def forbidden_capability(text: Optional[str]) -> Optional[str]:
    """Return the forbidden capability found in free text, or ``None``."""
    if not text or not isinstance(text, str):
        return None
    match = FORBIDDEN_OPERATION_PATTERN.search(text)
    return match.group(0).lower() if match else None


def normalize_target(target: Optional[str]) -> str:
    """Normalise a host/CIDR/URL target for exact comparison."""
    if not target or not isinstance(target, str):
        return ""
    value = target.strip().lower().rstrip(".")
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.hostname:
        value = parsed.hostname.lower()
    if ":" in value and not value.count(":") > 1:  # host:port, not IPv6
        value = value.split(":", 1)[0]
    return value


def is_broad_target(target: Optional[str]) -> bool:
    """Deny wildcard and internet-wide targets before any scope matching."""
    value = normalize_target(target)
    if not value or "*" in value or value in {"0.0.0.0/0", "::/0", "internet", "all"}:
        return True
    try:
        return ipaddress.ip_network(value, strict=False).num_addresses > 65536
    except ValueError:
        return False


def target_matches(target: str, allowed: str) -> bool:
    """Exact host match or CIDR containment only — never a prefix match."""
    candidate = normalize_target(target)
    permitted = normalize_target(allowed)
    if not candidate or not permitted or "*" in permitted:
        return False
    if candidate == permitted:
        return True
    try:
        address = ipaddress.ip_address(candidate)
        return address in ipaddress.ip_network(permitted, strict=False)
    except ValueError:
        return False


def scope_targets(scope: Dict[str, Any]) -> List[str]:
    configured = scope.get("targets")
    if isinstance(configured, list):
        return [str(item) for item in configured if item]
    single = scope.get("target")
    return [str(single)] if single else []


def scope_operations(scope: Dict[str, Any]) -> List[str]:
    configured = scope.get("allowed_operations")
    if isinstance(configured, list) and configured:
        return [str(item) for item in configured]
    return ["read"]


def _not_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > datetime.now(timezone.utc)


class AuthorisedTargetPolicy:
    """Verify a target/operation against signed Creator authority."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def verify(
        self,
        target: str,
        operation: str = "read",
        *,
        target_type: Optional[str] = None,
        require_write: bool = False,
    ) -> Dict[str, Any]:
        capability = forbidden_capability(target)
        if capability or is_broad_target(target):
            raise AuthorisedTargetDenied("wildcard, broad or offensive targets are forbidden")
        capability = forbidden_capability(operation)
        if capability:
            raise AuthorisedTargetDenied(
                f"operation requests a prohibited capability: {capability}"
            )

        result = await self.db.execute(
            select(CreatorAuthorization).where(
                CreatorAuthorization.action_type == AUTHORIZATION_ACTION,
                CreatorAuthorization.is_active.is_(True),
            )
        )
        approvals = CreatorApprovalService(self.db)
        for authorization in result.scalars().all():
            if authorization.revoked_at or not _not_expired(authorization.expires_at):  # type: ignore[arg-type]
                continue
            scope: Any = authorization.scope or {}
            if target_type and scope.get("target_type") not in (None, target_type):
                continue
            if not any(target_matches(target, item) for item in scope_targets(scope)):
                continue
            if operation not in scope_operations(scope):
                continue
            if require_write and not scope.get("allow_write", False):
                continue
            authority = await approvals.check_authorization(
                AUTHORIZATION_ACTION,
                target_ref=authorization.target_ref or normalize_target(target),  # type: ignore[arg-type]
            )
            if not authority.get("authorized"):
                continue
            if authority.get("authorization_id") != str(authorization.id):
                continue
            return {
                "authorized": True,
                "authorization_id": str(authorization.id),
                "signer_id": authorization.signer_id,
                "target": normalize_target(target),
                "operation": operation,
                "target_type": scope.get("target_type"),
                "allow_write": bool(scope.get("allow_write", False)),
                "expires_at": authority.get("expires_at"),
            }
        raise AuthorisedTargetDenied(
            "no active signed Creator authorization covers this target and operation"
        )
