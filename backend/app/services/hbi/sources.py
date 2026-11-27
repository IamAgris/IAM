"""Document 26 (OD-45): authorised live-source access.

No source is fetched unless it is explicitly registered with a licence and a
permitted purpose. Network access is injected, so this module never calls the
internet by itself and remains fully testable offline.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse


class SourceNotAuthorised(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class AuthorisedSource:
    source_id: str
    domain: str
    source_type: str
    licence: str
    permitted_purpose: str = "research"
    scope: str = "aggregate"
    require_robots: bool = True


class LiveSourceRegistry:
    def __init__(self):
        self.sources: Dict[str, AuthorisedSource] = {}

    def register(self, source: AuthorisedSource) -> None:
        if not source.licence:
            raise SourceNotAuthorised("licence_required")
        if source.scope != "aggregate":
            raise SourceNotAuthorised("individual_scope_not_permitted")
        self.sources[source.source_id] = source

    def authorise(self, url: str) -> AuthorisedSource:
        domain = (urlparse(url).netloc or "").lower()
        for source in self.sources.values():
            if domain == source.domain.lower() or domain.endswith("." + source.domain.lower()):
                return source
        raise SourceNotAuthorised("domain_not_allowlisted")

    def fetch(self, url: str, fetcher: Optional[Callable[[str], Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Fetch through an injected, policy-enforcing transport."""
        source = self.authorise(url)
        if fetcher is None:
            raise SourceNotAuthorised("no_authorised_fetcher_configured")
        payload = fetcher(url)
        if source.require_robots and payload.get("robots_allowed") is False:
            raise SourceNotAuthorised("robots_disallowed")
        if payload.get("licence") and payload["licence"] != source.licence:
            raise SourceNotAuthorised("licence_mismatch")
        return {
            "source_id": source.source_id,
            "source_type": source.source_type,
            "licence": source.licence,
            "permitted_purpose": source.permitted_purpose,
            "scope": source.scope,
            "url": url,
            "title": payload.get("title", url),
            "text": payload.get("text", ""),
            "collection_date": payload.get("collection_date"),
        }

    def list(self) -> List[Dict[str, Any]]:
        return [
            {
                "source_id": s.source_id, "domain": s.domain, "source_type": s.source_type,
                "licence": s.licence, "permitted_purpose": s.permitted_purpose,
                "require_robots": s.require_robots,
            }
            for s in self.sources.values()
        ]
