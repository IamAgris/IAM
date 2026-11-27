"""UWAIE browser engine adapters (Doc 29 WP-01).

A small adapter contract replaces the direct ``getattr(playwright, engine)``
switch. Missing engine runtimes fail closed — no silent fallback to Chromium.
"""

from typing import Any, Dict, Optional

from app.core.config import settings


class BrowserEngineUnavailable(RuntimeError):
    """Raised when an allowed engine is not present in the Playwright runtime."""


class EngineAdapter:
    name = "abstract"

    def capabilities(self) -> Dict[str, Any]:
        return {}

    def engine(self, playwright: Any) -> Any:
        candidate = getattr(playwright, self.name, None)
        if candidate is None:
            raise BrowserEngineUnavailable(
                f"browser engine '{self.name}' is not installed in this Playwright runtime"
            )
        return candidate

    async def new_context(self, browser: Any, **kwargs: Any) -> Any:
        return await browser.new_context(**kwargs)


class ChromiumAdapter(EngineAdapter):
    name = "chromium"

    def capabilities(self):
        return {"screenshots": True, "pdf": True, "headless": True}


class FirefoxAdapter(EngineAdapter):
    name = "firefox"

    def capabilities(self):
        return {"screenshots": True, "pdf": False, "headless": True}


class WebKitAdapter(EngineAdapter):
    name = "webkit"

    def capabilities(self):
        return {"screenshots": True, "pdf": False, "headless": True}


ADAPTERS = {
    adapter.name: adapter
    for adapter in (ChromiumAdapter(), FirefoxAdapter(), WebKitAdapter())
}
ENGINE_ALLOWLIST = tuple(ADAPTERS)


def get_adapter(name: Optional[str] = None) -> EngineAdapter:
    engine = name or settings.uwai_browser_engine
    if engine not in ADAPTERS:
        raise BrowserEngineUnavailable(f"unsupported browser engine: {engine}")
    return ADAPTERS[engine]


def available_engines(playwright: Any) -> Dict[str, Dict[str, Any]]:
    """Probe installed runtimes without launching a browser."""
    result = {}
    for name, adapter in ADAPTERS.items():
        try:
            adapter.engine(playwright)
            result[name] = adapter.capabilities()
        except BrowserEngineUnavailable:
            continue
    return result
