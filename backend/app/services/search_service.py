"""Search service - pluggable search API providers for independent research"""

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

    def __init__(self):
        self.provider = "duckduckgo"  # default: no API key required
        self.brave_api_key = settings.brave_api_key if hasattr(settings, 'brave_api_key') else None
        self.google_api_key = settings.google_api_key
        self.google_cx = settings.google_cx if hasattr(settings, 'google_cx') else None

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
        else:
            # Free fallback: Wikipedia public API (no key, no bot protection)
            return await self._search_wikipedia(query, max_results)

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
                        "X-Subscription-Token": self.brave_api_key,
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


# Singleton instance
search_service = SearchService()
