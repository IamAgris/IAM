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

# DuckDuckGo's HTML endpoint rejects generic bot UAs with HTTP 403. A browser-
# shaped UA is required for the free, key-less path to return any results.
# This is a request header only — no credentials or provider internals.
_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


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
        elif provider == "google-html":
            # Best-effort public results page, no key and no API guarantee.
            return await self._search_google_html(query, max_results)
        elif provider == "brave-html":
            # Best-effort public results page, no key and no API guarantee.
            return await self._search_brave_html(query, max_results)
        elif provider == "google-news-rss":
            return await self._search_google_news_rss(query, max_results)
        elif provider == "bing-news-rss":
            return await self._search_bing_news_rss(query, max_results)
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
                    headers={"User-Agent": _BROWSER_USER_AGENT},
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

    @staticmethod
    def _public_page_blocked(status_code: int, page: str) -> str:
        """Best-effort bot-protection detection for public search pages."""
        if status_code in (403, 429, 503, 202):
            return f"HTTP {status_code} (bot protection or rate limit)"
        title = re.search(r"<title[^>]*>(.*?)</title>", page[:20000], re.I | re.S)
        title_text = html_lib.unescape(re.sub(r"<[^>]+>", "", title.group(1))) if title else ""
        if re.search(
            r"captcha|unusual traffic|verify you are human|access denied|robot check",
            title_text,
            re.I,
        ):
            return "bot protection page returned"
        return ""

    @staticmethod
    def _parse_public_anchors(
        page: str, max_results: int, exclude_domains: tuple[str, ...]
    ) -> List[Dict[str, Any]]:
        """Extract outbound result links from a public search results page."""
        results: List[Dict[str, Any]] = []
        anchors = re.findall(
            r'<a\b[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.I | re.S
        )
        seen: set[str] = set()
        for href, inner in anchors:
            url = html_lib.unescape(href)
            if "/url?q=" in url:
                url = urllib.parse.unquote(url.split("/url?q=", 1)[1].split("&", 1)[0])
            if not url.startswith(("http://", "https://")):
                continue
            domain = urllib.parse.urlparse(url).netloc.lower()
            if any(exclude in domain for exclude in exclude_domains):
                continue
            title = html_lib.unescape(re.sub(r"<[^>]+>", " ", inner))
            title = re.sub(r"\s+", " ", title).strip()[:200]
            if len(title) < 5 or url in seen:
                continue
            seen.add(url)
            results.append({"title": title, "url": url[:1000], "description": ""})
            if len(results) >= max_results:
                break
        return results

    async def _search_public_page(
        self, query: str, max_results: int, name: str, url: str
    ) -> Dict[str, Any]:
        """Best-effort public HTML search — no key, no official API guarantee."""
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    url,
                    params={"q": query},
                    headers={
                        "User-Agent": _BROWSER_USER_AGENT,
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                    timeout=20.0,
                )
            blocked = self._public_page_blocked(response.status_code, response.text)
            if blocked:
                return {
                    "query": query,
                    "provider": name,
                    "results": [],
                    "error": blocked,
                    "searched_at": datetime.utcnow().isoformat(),
                }
            exclude = ("google.", "brave.com", "duckduckgo.", "search.")
            results = self._parse_public_anchors(response.text, max_results, exclude)
            if not results:
                return {
                    "query": query,
                    "provider": name,
                    "results": [],
                    "error": "no parseable public results",
                    "searched_at": datetime.utcnow().isoformat(),
                }
            return {
                "query": query,
                "provider": name,
                "results": results,
                "searched_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.warning(f"{name} public search failed: {exc}")
            return {
                "query": query,
                "provider": name,
                "results": [],
                "error": str(exc)[:200],
                "searched_at": datetime.utcnow().isoformat(),
            }

    async def _search_google_html(self, query: str, max_results: int) -> Dict[str, Any]:
        return await self._search_public_page(
            query, max_results, "google-html", "https://www.google.com/search"
        )

    async def _search_brave_html(self, query: str, max_results: int) -> Dict[str, Any]:
        return await self._search_public_page(
            query, max_results, "brave-html", "https://search.brave.com/search"
        )

    @staticmethod
    def _rss_tag(block: str, tag: str) -> str:
        match = re.search(
            rf"<{tag}[^>]*>(.*?)</{tag}>", block, re.IGNORECASE | re.DOTALL
        )
        if not match:
            return ""
        return html_lib.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()

    async def _search_news_rss(
        self, query: str, max_results: int, name: str, base_url: str, params: Dict[str, str]
    ) -> Dict[str, Any]:
        """Keyless public news RSS — current items with dates and sources."""
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    base_url,
                    params={"q": query, **params},
                    headers={"User-Agent": _BROWSER_USER_AGENT},
                    timeout=20.0,
                )
            blocked = self._public_page_blocked(response.status_code, response.text)
            if blocked:
                return {
                    "query": query,
                    "provider": name,
                    "results": [],
                    "error": blocked,
                    "searched_at": datetime.utcnow().isoformat(),
                }
            results: List[Dict[str, Any]] = []
            for block in re.findall(
                r"<item>(.*?)</item>", response.text, re.IGNORECASE | re.DOTALL
            ):
                link = self._rss_tag(block, "link")
                title = self._rss_tag(block, "title")
                if not link.startswith(("http://", "https://")) or not title:
                    continue
                if "apiclick.aspx" in link and "url=" in link:
                    # Bing wraps the publisher URL in a redirect; keep the
                    # original source link for accurate provenance.
                    link = urllib.parse.unquote(link.split("url=", 1)[1].split("&", 1)[0])
                source_match = re.search(
                    r'<source[^>]*url="([^"]+)"', block, re.IGNORECASE
                )
                source = (
                    urllib.parse.urlparse(source_match.group(1)).netloc
                    if source_match
                    else urllib.parse.urlparse(link).netloc
                )
                results.append(
                    {
                        "title": title[:200],
                        "url": link[:1000],
                        "description": "",
                        "source": source,
                        "published": self._rss_tag(block, "pubDate")[:80],
                    }
                )
                if len(results) >= max_results:
                    break
            if not results:
                return {
                    "query": query,
                    "provider": name,
                    "results": [],
                    "error": "no parseable news items",
                    "searched_at": datetime.utcnow().isoformat(),
                }
            return {
                "query": query,
                "provider": name,
                "results": results,
                "searched_at": datetime.utcnow().isoformat(),
            }
        except Exception as exc:
            logger.warning(f"{name} news RSS failed: {exc}")
            return {
                "query": query,
                "provider": name,
                "results": [],
                "error": str(exc)[:200],
                "searched_at": datetime.utcnow().isoformat(),
            }

    async def _search_google_news_rss(self, query: str, max_results: int) -> Dict[str, Any]:
        return await self._search_news_rss(
            query,
            max_results,
            "google-news-rss",
            "https://news.google.com/rss/search",
            {"hl": "en-US", "gl": "US", "ceid": "US:en"},
        )

    async def _search_bing_news_rss(self, query: str, max_results: int) -> Dict[str, Any]:
        return await self._search_news_rss(
            query,
            max_results,
            "bing-news-rss",
            "https://www.bing.com/news/search",
            {"format": "RSS"},
        )

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
                    headers={"User-Agent": _BROWSER_USER_AGENT},
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
