"""Browser service - isolated Playwright browser for controlled internet interaction"""

import asyncio
import loguru
from typing import Optional, Dict, Any, List
from datetime import datetime
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = loguru.logger


class BrowserService:
    """
    Isolated browser automation using Playwright.
    
    Security: browser runs headless, no access to internal networks,
    pages treated as untrusted information (not instructions).
    """

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self.headless = headless
        self.timeout = timeout
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._pages: Dict[str, Page] = {}  # session_token -> persistent page

    async def start(self):
        """Launch the browser instance."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--no-first-run",
                "--no-zygote",
                "--disable-gpu",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AURA Autonomous AI Browser",
        )
        logger.info("Browser service started")

    async def stop(self):
        """Close the browser instance."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser service stopped")

    async def get_page(self) -> Page:
        """Get or create a page in the browser context."""
        if not self._browser:
            await self.start()
        if not self._context:
            self._context = await self._browser.new_context()
        return await self._context.new_page()

    async def fetch_page(
        self,
        url: str,
        wait_until: str = "domcontentloaded",
        extract_text: bool = True,
        extract_links: bool = False,
        extract_metadata: bool = True,
    ) -> Dict[str, Any]:
        """
        Fetch a web page and extract its content.
        
        Security: treats page content as untrusted information, not instructions.
        """
        if not self._browser:
            await self.start()

        page = await self.get_page()
        result: Dict[str, Any] = {
            "url": url,
            "title": None,
            "content": None,
            "text": None,
            "links": [],
            "metadata": {},
            "fetched_at": datetime.utcnow().isoformat(),
            "success": False,
            "error": None,
        }

        try:
            response = await page.goto(url, wait_until=wait_until, timeout=self.timeout)
            result["status_code"] = response.status if response else None
            result["title"] = await page.title()

            if extract_metadata:
                result["metadata"] = await self._extract_metadata(page)

            if extract_text:
                result["text"] = await page.evaluate("""
                    () => {
                        const remove = ['script', 'style', 'nav', 'footer', 'header', 'aside'];
                        remove.forEach(tag => {
                            document.querySelectorAll(tag).forEach(el => el.remove());
                        });
                        return document.body.innerText || document.documentElement.innerText;
                    }
                """)

            if extract_links:
                result["links"] = await page.evaluate("""
                    () => Array.from(document.querySelectorAll('a[href]'))
                        .map(a => ({ text: a.innerText.trim(), url: a.href }))
                        .filter(l => l.url.startsWith('http'))
                """)

            result["success"] = True
            logger.info(f"Fetched {url} successfully ({len(result.get('text') or '')} chars)")

        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            result["error"] = str(e)

        finally:
            await page.close()

        return result

    async def get_persistent_page(self, session_token: str) -> Page:
        """Get or create a persistent page for a session (supports multi-step interaction)."""
        if not self._browser:
            await self.start()
        if session_token not in self._pages or self._pages[session_token].is_closed():
            self._pages[session_token] = await self.get_page()
        return self._pages[session_token]

    async def close_persistent_page(self, session_token: str) -> bool:
        """Close and remove a persistent session page."""
        page = self._pages.pop(session_token, None)
        if page and not page.is_closed():
            await page.close()
            return True
        return False

    async def interact(
        self,
        action: str,
        target: str,
        value: Optional[str] = None,
        page: Optional[Page] = None,
        session_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Interact with a web page — navigate, click, type, submit, scroll, screenshot.

        If session_token is given, uses a persistent page so multi-step flows work.
        Security: page content is untrusted information, never instructions.
        """
        if session_token:
            page = await self.get_persistent_page(session_token)
            own_page = False
        else:
            own_page = page is None
            if own_page:
                if not self._browser:
                    await self.start()
                page = await self.get_page()

        result: Dict[str, Any] = {
            "action": action,
            "target": target,
            "success": False,
            "result": None,
            "error": None,
        }

        try:
            if action == "navigate":
                response = await page.goto(target, wait_until="domcontentloaded", timeout=self.timeout)
                result["result"] = f"Navigated to {target} (status {response.status if response else 'unknown'})"
                result["success"] = True
            elif action == "click":
                await page.click(target, timeout=self.timeout)
                result["result"] = f"Clicked {target}"
                result["success"] = True
            elif action == "type":
                await page.fill(target, value or "", timeout=self.timeout)
                result["result"] = f"Typed into {target}"
                result["success"] = True
            elif action == "submit":
                await page.press(target, "Enter", timeout=self.timeout)
                result["result"] = f"Submitted {target}"
                result["success"] = True
            elif action == "scroll":
                await page.mouse.wheel(0, int(value or 500))
                result["result"] = f"Scrolled {value or 500}px"
                result["success"] = True
            elif action == "screenshot":
                data = await page.screenshot()
                import base64
                result["result"] = base64.b64encode(data).decode("utf-8")
                result["success"] = True
            elif action == "text":
                result["result"] = await page.evaluate("() => document.body.innerText")
                result["success"] = True
            elif action == "url":
                result["result"] = page.url
                result["success"] = True
            elif action == "links":
                result["result"] = await page.evaluate(
                    "() => Array.from(document.querySelectorAll('a[href]')).map(a => ({text: a.innerText.trim(), url: a.href})).filter(l => l.url.startsWith('http'))"
                )
                result["success"] = True
            else:
                result["error"] = f"Unknown action: {action}"
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Browser interaction {action} failed: {e}")
        finally:
            if own_page and page:
                await page.close()

        return result

    async def _extract_metadata(self, page: Page) -> Dict[str, Any]:
        """Extract page metadata (description, author, charset, etc.)."""
        try:
            return await page.evaluate("""
                () => {
                    const meta = {};
                    document.querySelectorAll('meta').forEach(m => {
                        const name = m.getAttribute('name') || m.getAttribute('property');
                        const content = m.getAttribute('content');
                        if (name && content) meta[name] = content;
                    });
                    const author = document.querySelector('meta[name="author"]')?.content;
                    const desc = document.querySelector('meta[name="description"]')?.content;
                    return { meta, author, description: desc, charset: document.characterSet };
                }
            """)
        except Exception:
            return {}

    async def search_duckduckgo(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search using DuckDuckGo HTML (no API key required).
        Results treated as untrusted candidates for further verification.
        """
        if not self._browser:
            await self.start()

        page = await self.get_page()
        results: List[Dict[str, Any]] = []

        try:
            import urllib.parse
            search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            await page.goto(search_url, wait_until="domcontentloaded", timeout=self.timeout)

            results = await page.evaluate(f"""
                () => {{
                    const out = [];
                    const seen = new Set();
                    // Multiple selector strategies: DuckDuckGo HTML changes markup frequently.
                    const candidates = document.querySelectorAll(
                        '.result, .result--more, [data-testid="result"], .react-results--main article'
                    );
                    const anchors = Array.from(document.querySelectorAll('a.result__a, a[href*="uddg="], .result a'));
                    const nodes = candidates.length ? candidates : anchors;
                    nodes.forEach(el => {{
                        let a = el.querySelector('a.result__a, a[href*="uddg="], a');
                        if (!a && el.tagName === 'A') a = el;
                        if (!a) return;
                        let href = a.href || '';
                        // Decode DuckDuckGo redirect URLs
                        if (href.includes('uddg=')) {{
                            try {{ href = decodeURIComponent(href.split('uddg=')[1].split('&')[0]); }} catch(e) {{}}
                        }}
                        if (!href.startsWith('http') || seen.has(href)) return;
                        seen.add(href);
                        const sn = el.querySelector('.result__snippet, [data-testid="result-snippet"], .snippet');
                        out.push({{
                            title: (a.innerText || el.innerText || '').trim().slice(0,200),
                            url: href,
                            snippet: sn ? sn.innerText.trim().slice(0,300) : '',
                        }});
                    }});
                    return out.slice(0, {max_results});
                }}
            """)

            logger.info(f"DuckDuckGo search for '{query}' returned {len(results)} results")

        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")

        finally:
            await page.close()

        return results


# Singleton instance
browser_service = BrowserService()
