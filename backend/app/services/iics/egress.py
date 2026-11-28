"""Single deterministic egress decision point for all outbound HTTP(S).

IICS gap closure §2.1. Every outbound request from research, browse, API
connector and download paths must pass this gate. DNS rebinding is addressed by
resolving the host before connect and pinning the validated address; redirects
are re-assessed rather than trusted.

``fetch_pinned`` is the transport used by callers that must not be able to reach
internal or metadata endpoints. It connects only to the address returned by
``assess`` while keeping the original hostname for HTTP Host, TLS SNI and
certificate verification.
"""

from __future__ import annotations

import asyncio
import http.client
import ipaddress
import socket
import ssl
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Union
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
class PinnedFetchResult:
    """Result of a redirect-aware fetch whose socket used a pinned address."""

    ok: bool
    url: str
    status_code: Optional[int] = None
    content_type: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    truncated: bool = False
    decision: Optional[Dict[str, Any]] = None
    error: str = ""
    redirect_location: str = ""


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


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """HTTP connection whose TCP peer is the validated address, not a fresh DNS lookup."""

    def __init__(self, host: str, port: Optional[int], pinned: str, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self._pinned = pinned

    def connect(self) -> None:
        # codeql[py/full-ssrf] pinned address passed EgressGateway.assess: scheme, host, DNS and private/metadata checks.
        self.sock = socket.create_connection((self._pinned, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection pinned to a validated IP with TLS SNI on the original host."""

    def __init__(
        self,
        host: str,
        port: Optional[int],
        pinned: str,
        timeout: float,
        context: ssl.SSLContext,
    ) -> None:
        super().__init__(host, port, timeout=timeout, context=context)
        self._pinned = pinned
        self._ssl_context = context

    def connect(self) -> None:
        # codeql[py/full-ssrf] pinned address passed EgressGateway.assess: scheme, host, DNS and private/metadata checks.
        sock = socket.create_connection((self._pinned, self.port), self.timeout)
        # server_hostname=self.host preserves SNI and certificate hostname verification.
        self.sock = self._ssl_context.wrap_socket(sock, server_hostname=self.host)


def _http_request(
    url: str,
    pinned: str,
    *,
    timeout: float,
    max_bytes: int,
    method: str = "GET",
    headers: Optional[Mapping[str, str]] = None,
) -> PinnedFetchResult:
    """Perform one request against a pinned address; caller re-assesses redirects."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = parsed.port
    target = parsed.path or "/"
    if parsed.query:
        target = f"{target}?{parsed.query}"
    context = ssl.create_default_context()
    conn: Union[_PinnedHTTPConnection, _PinnedHTTPSConnection]
    if parsed.scheme == "https":
        conn = _PinnedHTTPSConnection(host, port, pinned, timeout, context)
    else:
        conn = _PinnedHTTPConnection(host, port, pinned, timeout)
    try:
        # codeql[py/full-ssrf] URL was assessed by EgressGateway.assess; the socket connects only to the pinned address.
        conn.request(method, target, headers=dict(headers or {}))
        response = conn.getresponse()
        chunks: list[bytes] = []
        total = 0
        truncated = False
        while True:
            remaining = max_bytes + 1 - total
            chunk = response.read(min(65536, max(1, remaining)))
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                truncated = True
                chunks.append(chunk[: max(0, max_bytes - (total - len(chunk)))])
                break
            chunks.append(chunk)
        return PinnedFetchResult(
            ok=True,
            url=url,
            status_code=int(response.status),
            content_type=str(response.getheader("content-type") or ""),
            headers={key.lower(): value for key, value in response.getheaders()},
            body=b"".join(chunks)[:max_bytes],
            truncated=truncated,
            redirect_location=str(response.getheader("location") or ""),
        )
    finally:
        conn.close()


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

    def fetch_pinned_sync(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        max_bytes: Optional[int] = None,
    ) -> PinnedFetchResult:
        """Sync core: pin each hop, re-assess every redirect, cap size and time.

        DNS is resolved by ``assess`` once per hop and the connection uses the
        returned address, so a rebinding answer between check and connect cannot
        redirect the socket to an internal service.
        """
        current = url
        limit = self.max_bytes if max_bytes is None else max_bytes
        for _ in range(self.max_redirects + 1):
            decision = self.assess(current)
            if not decision.allowed or decision.address is None:
                return PinnedFetchResult(
                    False,
                    current,
                    decision=decision.as_dict(),
                    error=f"egress_denied:{decision.reason}",
                )
            try:
                result = _http_request(
                    current,
                    decision.address,
                    timeout=self.timeout,
                    max_bytes=limit,
                    headers=headers,
                )
            except (OSError, http.client.HTTPException, ssl.SSLError, ValueError) as exc:
                return PinnedFetchResult(
                    False, current, decision=decision.as_dict(), error=type(exc).__name__
                )
            result = replace(result, url=current, decision=decision.as_dict())
            if result.status_code in (301, 302, 303, 307, 308) and result.redirect_location:
                current = str(httpx.URL(current).join(result.redirect_location))
                continue
            return result
        return PinnedFetchResult(
            False,
            current,
            decision=self.assess(current).as_dict(),
            error="too_many_redirects",
        )

    async def fetch_pinned(
        self,
        url: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
        max_bytes: Optional[int] = None,
    ) -> PinnedFetchResult:
        """Async wrapper around the same pinned, redirect-aware transport."""
        return await asyncio.to_thread(
            self.fetch_pinned_sync, url, headers=headers, max_bytes=max_bytes
        )

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


_default_gateway: EgressGateway | None = None


def default_gateway() -> EgressGateway:
    """Process-wide gateway used by every outbound path."""
    global _default_gateway
    if _default_gateway is None:
        _default_gateway = EgressGateway()
    return _default_gateway


def set_default_gateway(gateway: EgressGateway) -> None:
    """Replace the gateway (used by tests and controlled deployments)."""
    global _default_gateway
    _default_gateway = gateway


def enforce(url: str) -> EgressDecision:
    """Mandatory assessment before any outbound request."""
    return default_gateway().assess(url)


def decision_from_mapping(payload: Mapping[str, object]) -> EgressDecision:
    """Rebuild a decision from a stored audit record."""
    return EgressDecision(
        allowed=bool(payload.get("allowed", False)),
        reason=str(payload.get("reason", "")),
        host=str(payload.get("host", "")),
        address=payload.get("address"),  # type: ignore[arg-type]
        policy_version=str(payload.get("policy_version", "iics-egress-1")),
    )
