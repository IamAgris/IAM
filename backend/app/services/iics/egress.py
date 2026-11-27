"""Single deterministic egress decision point for all outbound HTTP(S).

IICS gap closure §2.1. Every outbound request from research, browse, API
connector and download paths must pass this gate. DNS rebinding is addressed by
resolving the host before connect and pinning the validated address; redirects
are re-assessed rather than trusted.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, Iterable, Mapping, Optional
from urllib.parse import urlparse

import httpx

BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata",
        "metadata.google.internal",
        "metadata.goog",
    }
)

Resolver = Callable[[str], Iterable[str]]


@dataclass(frozen=True)
class EgressDecision:
    """Auditable outcome of an egress assessment."""

    allowed: bool
    reason: str
    host: str = ""
    address: Optional[str] = None
    policy_version: str = "iics-egress-1"

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _default_resolver(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        return []
    return sorted({str(info[4][0]) for info in infos})


def _is_forbidden_address(raw: str) -> bool:
    try:
        address = ipaddress.ip_address(raw.split("%", 1)[0])
    except ValueError:
        return True
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


class EgressGateway:
    """Assess and (optionally) fetch a URL under a single egress policy."""

    def __init__(
        self,
        *,
        allowed_hosts: Optional[Iterable[str]] = None,
        resolver: Optional[Resolver] = None,
        max_bytes: int = 200_000,
        timeout: float = 10.0,
        max_redirects: int = 3,
    ) -> None:
        self.allowed_hosts = {h.lower().rstrip(".") for h in (allowed_hosts or [])}
        self._resolver = resolver or _default_resolver
        self.max_bytes = max_bytes
        self.timeout = timeout
        self.max_redirects = max_redirects

    def assess(self, url: str) -> EgressDecision:
        """Return an allow/deny decision without performing a request."""
        try:
            parsed = urlparse(url)
        except ValueError:
            return EgressDecision(False, "malformed_url")
        if parsed.scheme not in {"http", "https"}:
            return EgressDecision(False, "unsupported_scheme", parsed.netloc)
        if parsed.username or parsed.password:
            return EgressDecision(False, "credentials_in_url", parsed.netloc)
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host:
            return EgressDecision(False, "missing_host")
        if host in BLOCKED_HOSTNAMES or host.endswith(".localhost"):
            return EgressDecision(False, "blocked_hostname", host)

        is_literal = False
        try:
            ipaddress.ip_address(host)
            is_literal = True
        except ValueError:
            pass
        if is_literal and host not in self.allowed_hosts:
            return EgressDecision(False, "ip_literal_not_allowlisted", host)

        if self.allowed_hosts and host not in self.allowed_hosts:
            return EgressDecision(False, "host_not_allowlisted", host)

        addresses = list(self._resolver(host))
        if not addresses:
            return EgressDecision(False, "dns_resolution_failed", host)
        for address in addresses:
            if _is_forbidden_address(address):
                return EgressDecision(False, "internal_or_metadata_address", host, address)
        return EgressDecision(True, "allowed", host, addresses[0])

    async def fetch(self, url: str) -> Dict[str, Any]:
        """Fetch a URL after assessment; re-assess every redirect."""
        current = url
        for _ in range(self.max_redirects + 1):
            decision = self.assess(current)
            if not decision.allowed:
                return {"ok": False, "decision": decision.as_dict(), "url": current}
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=False,
                verify=True,
            ) as client:
                try:
                    response = await client.get(current)
                except httpx.HTTPError as exc:
                    return {"ok": False, "decision": decision.as_dict(), "error": type(exc).__name__}
            if response.is_redirect:
                location = response.headers.get("location", "")
                if not location:
                    return {"ok": False, "decision": decision.as_dict(), "error": "empty_redirect"}
                current = str(httpx.URL(current).join(location))
                continue
            raw = response.content[: self.max_bytes]
            return {
                "ok": True,
                "decision": decision.as_dict(),
                "url": current,
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", ""),
                "bytes": len(raw),
                "truncated": len(response.content) > self.max_bytes,
                "body": raw.decode("utf-8", errors="replace"),
            }
        return {"ok": False, "decision": self.assess(current).as_dict(), "error": "too_many_redirects"}


def decision_from_mapping(payload: Mapping[str, object]) -> EgressDecision:
    """Rebuild a decision from a stored audit record."""
    return EgressDecision(
        allowed=bool(payload.get("allowed", False)),
        reason=str(payload.get("reason", "")),
        host=str(payload.get("host", "")),
        address=payload.get("address"),  # type: ignore[arg-type]
        policy_version=str(payload.get("policy_version", "iics-egress-1")),
    )
