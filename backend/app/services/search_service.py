"""Search service - pluggable search API providers for independent research"""

import html as html_lib
import re
import urllib.parse

import httpx
import loguru
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.config import settings

logger = loguru.logger


class SearchService:
    """
    Search service supporting multiple providers.
    
    Results are treated as untrusted candidates requiring verification
    through multiple-source evaluation before being stored as knowledge.
    """

    def __init__(self) -> None:
        self.provider = "duckduckgo"  # default: no API key required
        self.brave_api_key = settings.brave_api_key if hasattr(settings, 'brave_api_key') else None
        self.google_api_key = settings.google_api_key
        self.google_cx = settings.google_cx if hasattr(settings, 'google_cx') else None
        self.searxng_url = settings.iam_search_searxng_url.rstrip("/")
        self.tavily_api_key = settings.iam_search_tavily_api_key or None

    async def search(
        self,
        query: str,
        max_results: int = 10,
        provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Search the web and return results with provenance.
        
        Returns: { query, provider, results: [...], searched_at }
        """
        provider = provider or self.provider

        if provider == "brave" and self.brave_api_key:
            return await self._search_brave(query, max_results)
        elif provider == "google" and self.google_api_key and self.google_cx:
            return await self._search_google(query, max_results)
        elif provider == "duckduckgo":
            # Free, no-key web search via the public HTML endpoint.
            return await self._search_duckduckgo(query, max_results)
        elif provider == "searxng":
            return await self._search_searxng(query, max_results)
        elif provider == "tavily":
            if not self.tavily_api_key:
                # Never silently substitute another provider for a paid one.
                return {
                    "query": query,
                    "provider": "tavily",
                    "results": [],
                    "error": "Tavily API key not configured; paid search requires signed authorisation",
                    "searched_at": datetime.utcnow().isoformat(),
                }
            return await self._search_tavily(query, max_results)
        else:
            # Free fallback: Wikipedia public API (no key, no bot protection).
            # Wikipedia is background, not live evidence (proposed Doc 32).
            return await self._search_wikipedia(query, max_results)

    async def _search_duckduckgo(self, query: str, max_results: int) -> Dict[str, Any]:
        """Free DuckDuckGo HTML search — no key, no browser, no invented data."""
        results: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={"User-Agent": "IAM-Research/1.0 (public web research)"},
                    timeout=20.0,
                )
            if response.status_code != 200:
                return {
                    "query": query,
                    "provider": "duckduckgo",
                    "results": [],
                    "error": f"HTTP {response.status_code}",
                    "searched_at": datetime.utcnow().isoformat(),
                }
            page = response.text
            anchor = re.compile(
                r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                re.IGNORECASE | re.DOTALL,
            )
            snippet_re = re.compile(
                r'class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
                re.IGNORECASE | re.DOTALL,
            )
            for match in anchor.finditer(page):
                url = html_lib.unescape(match.group(1))
                if "uddg=" in url:
                    url = urllib.parse.unquote(
                        url.split("uddg=", 1)[1].split("&", 1)[0]
                    )
                title = re.sub(r"<[^>]+>", "", match.group(2))
                title = html_lib.unescape(title).strip()
                if not url.startswith("http") or not title:
                    continue
                tail = page[match.end() : match.end() + 2000]
                snippet_match = snippet_re.search(tail)
                snippet = ""
                if snippet_match:
                    snippet = html_lib.unescape(
                        re.sub(r"<[^>]+>", "", snippet_match.group(1))
                    ).strip()
                results.append(
                    {"title": title[:200], "url": url[:1000], "description": snippet[:300]}
                )
                if len(results) >= max_results:
                    break
        except Exception as exc:
            logger.warning(f"DuckDuckGo HTML search failed: {exc}")
            return {
                "query": query,
                "provider": "duckduckgo",
                "results": [],
                "error": str(exc)[:200],
                "searched_at": datetime.utcnow().isoformat(),
            }
        return {
            "query": query,
            "provider": "duckduckgo",
            "results": results,
            "searched_at": datetime.utcnow().isoformat(),
        }

    async def _search_wikipedia(self, query: str, max_results: int) -> Dict[str, Any]:
        """Search Wikipedia's public API — free, no key, respects access norms."""
        results = []
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query", "list": "search", "srsearch": query,
                        "format": "json", "srlimit": max_results,
                    },
                    headers={"User-Agent": "IAM-Research/1.0 (autonomous research)"},
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    for item in resp.json().get("query", {}).get("search", []):
                        title = item.get("title", "")
                        snippet = item.get("snippet", "")
                        for tag in ("<span class=\"searchmatch\">", "</span>", "<p>", "</p>"):
                            snippet = snippet.replace(tag, "")
                        results.append({
                            "title": title,
                            "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
                            "description": snippet[:300],
                        })
        except Exception as e:
            logger.warning(f"Wikipedia search failed: {e}")
        return {
            "query": query,
            "provider": "wikipedia",
            "results": results,
            "searched_at": datetime.utcnow().isoformat(),
        }

    async def _search_brave(self, query: str, max_results: int) -> Dict[str, Any]:
        """Brave Search API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={
                        "Accept": "application/json",
                        "X-Subscription-Token": str(self.brave_api_key or ""),
                    },
                    params={"q": query, "count": max_results},
                    timeout=30.0,
                )
                data = response.json()
                results = []
                for item in data.get("web", {}).get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "description": item.get("description", ""),
                        "age": item.get("age", ""),
                    })
                return {
                    "query": query,
                    "provider": "brave",
                    "results": results,
                    "searched_at": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Brave search failed: {e}")
            return {"query": query, "provider": "brave", "results": [], "error": str(e)}

    async def _search_google(self, query: str, max_results: int) -> Dict[str, Any]:
        """Google Custom Search API."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/customsearch/v1",
                    params={
                        "key": self.google_api_key,
                        "cx": self.google_cx,
                        "q": query,
                        "num": max_results,
                    },
                    timeout=30.0,
                )
                data = response.json()
                results = []
                for item in data.get("items", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "description": item.get("snippet", ""),
                    })
                return {
                    "query": query,
                    "provider": "google",
                    "results": results,
                    "searched_at": datetime.utcnow().isoformat(),
                }
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return {"query": query, "provider": "google", "results": [], "error": str(e)}


    async def _search_searxng(self, query: str, max_results: int) -> Dict[str, Any]:
        """Self-hosted SearXNG JSON API — free and provider-independent."""
        if not self.searxng_url:
            return {
                "query": query, "provider": "searxng", "results": [],
                "error": "SearXNG endpoint not configured",
                "searched_at": datetime.utcnow().isoformat(),
            }
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    f"{self.searxng_url}/search",
                    params={"q": query, "format": "json"},
                    headers={"User-Agent": "IAM-Research/1.0 (public web research)"},
                    timeout=20.0,
                )
            if response.status_code != 200:
                return {
                    "query": query, "provider": "searxng", "results": [],
                    "error": f"HTTP {response.status_code}",
                    "searched_at": datetime.utcnow().isoformat(),
                }
            results = [
                {
                    "title": str(item.get("title") or "")[:200],
                    "url": str(item.get("url") or ""),
                    "description": str(item.get("content") or "")[:300],
                }
                for item in (response.json().get("results") or [])[:max_results]
                if item.get("url")
            ]
            return {
                "query": query, "provider": "searxng", "results": results,
                "searched_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            return {
                "query": query, "provider": "searxng", "results": [],
                "error": str(exc)[:200], "searched_at": datetime.utcnow().isoformat(),
            }

    async def _search_tavily(self, query: str, max_results: int) -> Dict[str, Any]:
        """Paid Tavily adapter. Never called automatically by IAM (OD-04/OD-25)."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": self.tavily_api_key,
                        "query": query,
                        "max_results": max_results,
                    },
                    timeout=30.0,
                )
            data = response.json()
            results = [
                {
                    "title": str(item.get("title") or "")[:200],
                    "url": str(item.get("url") or ""),
                    "description": str(item.get("content") or "")[:300],
                }
                for item in (data.get("results") or [])[:max_results]
                if item.get("url")
            ]
            return {
                "query": query, "provider": "tavily", "results": results,
                "searched_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            return {
                "query": query, "provider": "tavily", "results": [],
                "error": str(exc)[:200], "searched_at": datetime.utcnow().isoformat(),
            }


# Singleton instance
search_service = SearchService()
