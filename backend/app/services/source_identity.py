"""Stable, privacy-safe identifiers for public source nodes."""

import hashlib
from typing import Any, Dict
from urllib.parse import urlparse


def node_id_for_url(url: str) -> str:
    """Deterministic short id so research and recall refer to the same node."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]


def source_meta(url: str, title: str = "") -> Dict[str, Any]:
    return {
        "title": title or url,
        "domain": urlparse(url).netloc,
        "url": url,
        "node_id": node_id_for_url(url),
    }
