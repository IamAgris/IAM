"""Document 26 (OD-45): minimal HTTP transport for authorised public sources.

Only called through LiveSourceRegistry after allowlist, licence and purpose
checks. Respects robots.txt, enforces a byte cap and a short timeout.
"""

import json
from typing import Any, Dict
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from urllib.request import Request, urlopen

from app.services.iics.egress import enforce

_MAX_BYTES = 200_000
_TIMEOUT = 10
_USER_AGENT = "IAM-HBI-Research/1.0"


def _robots_allowed(url: str) -> bool:
    parsed = urlparse(url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
    parser = RobotFileParser()
    try:
        parser.set_url(robots_url)
        parser.read()
    except Exception:
        return False
    return parser.can_fetch(_USER_AGENT, url)


def fetch_json(url: str) -> Dict[str, Any]:
    """Fetch public JSON from an allowlisted/open API endpoint."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("unsupported_scheme")
    decision = enforce(url)
    if not decision.allowed:
        raise ValueError(f"egress_denied:{decision.reason}")
    request = Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=_TIMEOUT) as response:
        raw = response.read(_MAX_BYTES)
        payload = json.loads(raw.decode("utf-8", errors="ignore"))
        return payload if isinstance(payload, dict) else {}


def fetch(url: str) -> Dict[str, Any]:
    """Fetch a public document. Returns metadata and text, not a psychological claim."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("unsupported_scheme")
    decision = enforce(url)
    if not decision.allowed:
        raise ValueError(f"egress_denied:{decision.reason}")
    allowed = _robots_allowed(url)
    if not allowed:
        return {"robots_allowed": False, "text": "", "title": url}
    request = Request(url, headers={"User-Agent": _USER_AGENT})
    with urlopen(request, timeout=_TIMEOUT) as response:
        raw = response.read(_MAX_BYTES)
        return {
            "robots_allowed": True,
            "text": raw.decode("utf-8", errors="ignore"),
            "title": response.headers.get("Content-Disposition") or url,
            "collection_date": response.headers.get("Last-Modified"),
        }
