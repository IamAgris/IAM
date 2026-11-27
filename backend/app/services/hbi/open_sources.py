"""Document 27 (proposed OD-47): free/open research source adapters.

Uses official public APIs and recorded terms. No scraping, no bypassing
paywalls, no private data. Network access is injected so tests stay offline.
"""

from typing import Any, Callable, Dict, List

from app.services.hbi.schemas import ResearchDocumentInput

Adapter = Dict[str, Any]

ADAPTERS: Dict[str, Adapter] = {
    "openalex": {
        "kind": "api", "url": "https://api.openalex.org/works?search={query}&per-page={limit}",
        "fields": ("display_name", "abstract_inverted_index", "id"),
        "terms": "OpenAPI terms; metadata CC0; full-text rights vary",
    },
    "crossref": {
        "kind": "api", "url": "https://api.crossref.org/works?query={query}&rows={limit}",
        "fields": ("title", "abstract", "DOI"),
        "terms": "metadata reuse permitted with attribution; full text not included",
    },
    "europe_pmc": {
        "kind": "api", "url": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&format=json&pageSize={limit}",
        "fields": ("title", "abstractText", "id"),
        "terms": "abstracts/full text subject to individual article licences",
    },
    "semantic_scholar": {
        "kind": "api", "url": "https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit={limit}&fields=title,abstract,externalIds",
        "fields": ("title", "abstract", "externalIds"),
        "terms": "API terms; metadata only",
    },
    "wikidata": {
        "kind": "api", "url": "https://www.wikidata.org/w/api.php?action=wbsearchentities&search={query}&language=en&format=json&limit={limit}",
        "fields": ("label", "description", "id"),
        "terms": "CC0 structured data",
    },
    "doaj": {
        "kind": "api", "url": "https://doaj.org/api/search/articles/{query}?pageSize={limit}",
        "fields": ("title", "abstract", "id"),
        "terms": "open-access articles; check individual licences",
    },
    "core": {
        "kind": "api", "url": "https://api.core.ac.uk/v3/search/works?q={query}&limit={limit}",
        "fields": ("title", "abstract", "id"),
        "terms": "open-access aggregator; per-item rights",
    },
    "internet_archive": {
        "kind": "archive", "url": "https://archive.org/advancedsearch.php?q={query}&rows={limit}&output=json",
        "fields": ("title", "description", "identifier"),
        "terms": "per-item rights; public-domain subset preferred",
    },
}


def list_adapters() -> Dict[str, Any]:
    return {
        "count": len(ADAPTERS),
        "adapters": [
            {"name": name, "kind": item["kind"], "terms": item["terms"]}
            for name, item in ADAPTERS.items()
        ],
        "note": "Free sources still require per-item licence and purpose checks.",
    }


def _text_from_item(item: Dict[str, Any], fields: tuple[str, ...]) -> str:
    parts = []
    for field in fields:
        value = item.get(field)
        if isinstance(value, str) and value:
            parts.append(value)
        elif isinstance(value, dict):
            for nested in value.values():
                if isinstance(nested, str) and nested:
                    parts.append(nested)
    return " ".join(dict.fromkeys(parts))


async def fetch_documents(adapter_name: str, query: str, fetcher: Callable[[str], Dict[str, Any]],
                          limit: int = 5) -> Dict[str, Any]:
    """Fetch metadata from a free API through an injected transport."""
    adapter = ADAPTERS.get(adapter_name)
    if adapter is None:
        return {"error": "unknown_adapter", "adapter": adapter_name}
    import urllib.parse
    url = adapter["url"].format(query=urllib.parse.quote(query), limit=limit)
    payload = fetcher(url)
    raw = payload.get("results") or payload.get("items") or payload.get("response", {}).get("docs") or []
    if isinstance(raw, dict):
        raw = list(raw.values())
    documents = []
    for index, item in enumerate(raw[:limit]):
        if not isinstance(item, dict):
            continue
        text = _text_from_item(item, adapter["fields"])
        if len(text) < 30:
            continue
        documents.append(ResearchDocumentInput(
            source_id=f"{adapter_name}_{index}",
            title=str(item.get("title") or item.get("display_name") or item.get("label") or f"{adapter_name}_{index}")[:500],
            text=text[:20000],
            source_type="public_metadata",
            licence="recorded_terms",
            permitted_purpose="research",
        ))
    return {
        "adapter": adapter_name,
        "kind": adapter["kind"],
        "terms": adapter["terms"],
        "url": url,
        "documents": documents,
        "count": len(documents),
        "note": "Metadata only; per-item rights must be checked before retention or training.",
    }
