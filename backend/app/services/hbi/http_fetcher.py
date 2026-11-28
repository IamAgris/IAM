"""Document 26 (OD-45): minimal HTTP transport for authorised public sources.

Only called through LiveSourceRegistry after allowlist, licence and purpose
checks. All requests go through the shared pinned egress gateway, including
robots.txt, so a DNS-rebinding answer cannot turn an approved lookup into a
request to an internal or metadata endpoint. Respects robots.txt, enforces a
byte cap and a short timeout.
"""

import json
from typing import Any, Dict
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from app.services.iics.egress import EgressGateway

_MAX_BYTES = 200_000
_TIMEOUT = 10
_USER_AGENT = "IAM-HBI-Research/1.0"


def _gateway() -> EgressGateway:
    return EgressGateway(timeout=float(_TIMEOUT), max_bytes=_MAX_BYTES)


def _require_allowed(url: str) -> None:
    decision = _gateway().assess(url)
    if not decision.allowed:
        raise ValueError(f"egress_denied:{decision.reason}")


def _robots_allowed(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
    result = _gateway().fetch_pinned_sync(robots_url, headers={"User-Agent": _USER_AGENT})
    if not result.ok or result.status_code is None or result.status_code >= 400:
        return False
    parser = RobotFileParser()
    parser.parse(result.body.decode("utf-8", errors="replace").splitlines())
    return parser.can_fetch(_USER_AGENT, url)


def fetch_json(url: str) -> Dict[str, Any]:
    """Fetch public JSON from an allowlisted/open API endpoint."""
    result = _gateway().fetch_pinned_sync(
        url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"}
    )
    if not result.ok:
        raise ValueError(result.error)
    payload = json.loads(result.body.decode("utf-8", errors="ignore"))
    return payload if isinstance(payload, dict) else {}


def fetch(url: str) -> Dict[str, Any]:
    """Fetch a public document. Returns metadata and text, not a psychological claim."""
    _require_allowed(url)
    if not _robots_allowed(url):
        return {"robots_allowed": False, "text": "", "title": url}
    result = _gateway().fetch_pinned_sync(url, headers={"User-Agent": _USER_AGENT})
    if not result.ok:
        raise ValueError(result.error)
    return {
        "robots_allowed": True,
        "text": result.body.decode("utf-8", errors="ignore"),
        "title": result.headers.get("content-disposition") or url,
        "collection_date": result.headers.get("last-modified"),
    }
