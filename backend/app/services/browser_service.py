"""Browser service - isolated Playwright browser for controlled internet interaction"""

import asyncio
import os
import tempfile
import uuid
import loguru
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from app.core.config import settings
from app.services.browser_engine_adapters import (
    BrowserEngineUnavailable,
    available_engines,
    get_adapter,
)
from app.services.iics.egress import enforce as enforce_egress
from app.services.iics.threat_intel import DLPEngine
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = loguru.logger


class BrowserService:
    """
    Isolated browser automation using Playwright.
    
    Security: browser runs headless, no access to internal networks,
    pages treated as untrusted information (not instructions).
    """

    ENGINE_ALLOWLIST = ("chromium", "firefox", "webkit")

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,
        engine: Optional[str] = None,
    ):
        if not settings.browser_enabled:
            raise BrowserEngineUnavailable("browser automation is disabled by policy")
        self.headless = headless
        self.timeout = timeout
        self.engine = engine or settings.uwai_browser_engine
        if self.engine not in self.ENGINE_ALLOWLIST:
            raise ValueError(f"unsupported browser engine: {self.engine}")
        self.transfer_root = Path(
            settings.uwai_upload_root
            or str(Path(tempfile.gettempdir()) / "iam-web-uploads")
        ).resolve()
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None  # default compatibility context
        self._contexts: Dict[str, BrowserContext] = {}  # session_token -> isolated context
        self._session_meta: Dict[str, Dict[str, Any]] = {}
        self._pages: Dict[str, Page] = {}  # session_token -> primary persistent page
        self._tabs: Dict[str, Dict[str, Page]] = {}  # session_token -> tab_id -> page

    async def _ensure_browser(self) -> None:
        """Restart Playwright if a previous driver died or was disconnected."""
        connected = bool(self._browser) and bool(
            getattr(self._browser, "is_connected", lambda: True)()
        )
        if connected:
            return
        try:
            await self.stop()
        except Exception as exc:
            logger.warning(f"Browser cleanup before restart failed: {exc}")
        self._browser = None
        self._context = None
        self._playwright = None
        self._pages.clear()
        self._tabs.clear()
        self._contexts.clear()
        self._session_meta.clear()
        await self.start()

    async def start(self):
        """Launch the browser instance."""
        # The container installs browsers at /ms-playwright. Honour that path
        # even when the environment variable was not passed at container start.
        if os.path.isdir("/ms-playwright") and not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/ms-playwright"
        self._playwright = await async_playwright().start()
        self.transfer_root.mkdir(parents=True, exist_ok=True)
        adapter = get_adapter(self.engine)
        engine = adapter.engine(self._playwright)
        self._browser = await engine.launch(
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
        """Close the browser instance and every session context."""
        for token in list(self._contexts):
            await self.close_session(token)
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser service stopped")

    def _safe_transfer_path(self, name: str) -> Path:
        """Keep uploads/downloads inside the configured transfer root."""
        if not name or not isinstance(name, str):
            raise ValueError("file name is required")
        candidate = (self.transfer_root / Path(name).name).resolve()
        if self.transfer_root not in candidate.parents:
            raise ValueError("file path escapes the transfer root")
        return candidate

    async def get_page(self) -> Page:
        """Get or create a page in the default browser context."""
        await self._ensure_browser()
        if not self._context:
            self._context = await self._browser.new_context()
        return await self._context.new_page()

    async def _reap_expired(self) -> None:
        now = datetime.now(timezone.utc)
        for token, meta in list(self._session_meta.items()):
            age = (now - meta["created_at"]).total_seconds()
            if age > settings.browser_session_ttl_seconds:
                await self.close_session(token)

    async def open_session(
        self,
        session_token: str,
        *,
        mode: str = "headless",
        owner: str = "agent",
        permission_scope: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create an isolated browser context for one UWAIE session.

        Visible mode fails closed without a display and an explicit flag.
        Isolated mode gives the session its own context (no shared cookies).
        """
        if mode not in {"headless", "visible", "isolated"}:
            raise ValueError(f"unsupported session mode: {mode}")
        if mode == "visible" and (
            not settings.browser_visible_mode_enabled or not os.environ.get("DISPLAY")
        ):
            raise BrowserEngineUnavailable(
                "visible browser mode requires DISPLAY and BROWSER_VISIBLE_MODE_ENABLED"
            )
        if mode == "isolated" and not settings.browser_isolated_mode_enabled:
            raise BrowserEngineUnavailable("isolated browser mode is disabled by policy")

        await self._reap_expired()
        if session_token in self._contexts:
            return dict(self._session_meta[session_token])
        if len(self._contexts) >= settings.browser_max_concurrent_sessions:
            raise BrowserEngineUnavailable("browser session concurrency limit reached")

        await self._ensure_browser()
        browser = self._browser
        if browser is None:
            raise BrowserEngineUnavailable("browser engine is unavailable")
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AURA Autonomous AI Browser",
        )
        self._contexts[session_token] = context
        self._session_meta[session_token] = {
            "session_id": session_token,
            "mode": mode,
            "owner": owner,
            "actor_type": owner if owner in {"agent", "creator"} else "agent",
            "permission_scope": list(permission_scope or []),
            "engine": self.engine,
            "created_at": datetime.now(timezone.utc),
        }
        return dict(self._session_meta[session_token])

    async def close_session(self, session_token: str) -> bool:
        context = self._contexts.pop(session_token, None)
        self._session_meta.pop(session_token, None)
        self._pages.pop(session_token, None)
        self._tabs.pop(session_token, None)
        if context:
            await context.close()
            return True
        return False

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
        decision = enforce_egress(url)
        if not decision.allowed:
            return {
                "url": url,
                "success": False,
                "error": f"egress_denied:{decision.reason}",
                "text": None,
                "links": [],
                "metadata": {},
            }
        await self._ensure_browser()

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
        await self._ensure_browser()
        if session_token not in self._pages or self._pages[session_token].is_closed():
            self._pages[session_token] = await self.get_page()
        return self._pages[session_token]

    async def new_tab(self, session_token: str) -> str:
        """Open an additional tab inside the same isolated session context."""
        await self._ensure_browser()
        if not self._context:
            self._context = await self._browser.new_context()
        tab_id = uuid.uuid4().hex[:12]
        self._tabs.setdefault(session_token, {})[tab_id] = await self._context.new_page()
        return tab_id

    async def list_tabs(self, session_token: str) -> List[str]:
        tabs = self._tabs.get(session_token, {})
        return [tab_id for tab_id, page in tabs.items() if not page.is_closed()]

    async def get_tab(self, session_token: str, tab_id: str) -> Optional[Page]:
        page = self._tabs.get(session_token, {}).get(tab_id)
        if page and not page.is_closed():
            return page
        return None

    async def close_tab(self, session_token: str, tab_id: str) -> bool:
        page = self._tabs.get(session_token, {}).pop(tab_id, None)
        if page and not page.is_closed():
            await page.close()
            return True
        return False

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
        tab_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Interact with a web page — navigate, click, type, submit, scroll, screenshot.

        If session_token is given, uses a persistent page so multi-step flows work.
        Security: page content is untrusted information, never instructions.
        """
        if action == "new_tab":
            if not session_token:
                return {"action": action, "success": False, "error": "session_token required"}
            tab = await self.new_tab(session_token)
            return {"action": action, "target": tab, "result": tab, "success": True, "error": None}
        if action == "list_tabs":
            if not session_token:
                return {"action": action, "success": False, "error": "session_token required"}
            tabs = await self.list_tabs(session_token)
            return {"action": action, "target": "", "result": tabs, "success": True, "error": None}
        if action == "close_tab":
            if not session_token:
                return {"action": action, "success": False, "error": "session_token required"}
            closed = await self.close_tab(session_token, target)
            return {
                "action": action,
                "target": target,
                "result": closed,
                "success": closed,
                "error": None if closed else "tab not found",
            }
        if tab_id and session_token:
            tab_page = await self.get_tab(session_token, tab_id)
            if not tab_page:
                return {"action": action, "success": False, "error": "unknown tab"}
            page = tab_page
            own_page = False
        elif session_token:
            page = await self.get_persistent_page(session_token)
            own_page = False
        else:
            own_page = page is None
            if own_page:
                await self._ensure_browser()
                page = await self.get_page()

        result: Dict[str, Any] = {
            "action": action,
            "target": target,
            "success": False,
            "result": None,
            "error": None,
        }

        if action == "navigate":
            decision = enforce_egress(target)
            if not decision.allowed:
                result["error"] = f"egress_denied:{decision.reason}"
                return result
        if action in {"type", "upload", "submit"}:
            dlp = DLPEngine.check(f"{target}\n{value or ''}", "browser")
            if not dlp["allowed"]:
                result["error"] = f"dlp_blocked:{','.join(dlp['matched_labels'])}"
                return result

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
            elif action == "upload":
                path = self._safe_transfer_path(value or "")
                if not path.is_file():
                    raise FileNotFoundError("upload file is not present in the transfer root")
                await page.set_input_files(target, str(path), timeout=self.timeout)
                result["result"] = f"Uploaded {path.name}"
                result["success"] = True
            elif action == "download":
                async with page.expect_download(timeout=self.timeout) as download_info:
                    await page.click(target, timeout=self.timeout)
                download = await download_info.value
                destination = self._safe_transfer_path(download.suggested_filename)
                await download.save_as(str(destination))
                result["result"] = f"Downloaded {destination.name}"
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
        await self._ensure_browser()

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
