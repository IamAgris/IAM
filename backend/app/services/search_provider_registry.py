"""Search provider management (proposed Doc 32 §6).

Provider-independent adapters with health, quota/cost metadata and managed
failover. No provider is the sole gateway to the web. Paid providers are
excluded from automatic use; their use requires signed Creator authorisation
under OD-04/OD-25 via ``SEARCH_ACTION``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings

PAID_PROVIDERS = frozenset({"brave", "google", "tavily"})


@dataclass
class ProviderState:
    name: str
    free: bool
    enabled: bool = True
    healthy: bool = True
    calls: int = 0
    failures: int = 0
    last_error: str = ""


class SearchProviderRegistry:
    """Bounded, deterministic provider chain with health and usage counters."""

    def __init__(self) -> None:
        self._states: Dict[str, ProviderState] = {
            name: ProviderState(name=name, free=name not in PAID_PROVIDERS)
            for name in ("wikipedia", "duckduckgo", "searxng", "brave", "google", "tavily")
        }

    def reset(self) -> None:
        """Restore all providers to enabled/healthy (test and restart helper)."""
        self._states = {
            name: ProviderState(name=name, free=name not in PAID_PROVIDERS)
            for name in ("wikipedia", "duckduckgo", "searxng", "brave", "google", "tavily")
        }

    def state(self, name: str) -> ProviderState:
        return self._states.setdefault(
            name, ProviderState(name=name, free=name not in PAID_PROVIDERS)
        )

    def chain(self, *, free_only: bool = True) -> List[str]:
        configured = [
            name.strip().lower()
            for name in settings.iam_search_provider_order.split(",")
            if name.strip()
        ]
        return [
            name
            for name in configured
            if name in self._states
            and self.state(name).enabled
            and self.state(name).healthy
            and (not free_only or self.state(name).free)
        ]

    def enable(self, name: str, enabled: bool) -> None:
        self.state(name).enabled = bool(enabled)

    def record(self, name: str, *, ok: bool, error: str = "") -> None:
        state = self.state(name)
        state.calls += 1
        if ok:
            state.failures = 0
            state.last_error = ""
            state.healthy = True
        else:
            state.failures += 1
            state.last_error = error[:200]
            if state.failures >= 3:
                state.healthy = False

    def status(self) -> Dict[str, Dict[str, Any]]:
        return {
            name: {
                "free": state.free,
                "enabled": state.enabled,
                "healthy": state.healthy,
                "calls": state.calls,
                "failures": state.failures,
                "last_error": state.last_error,
            }
            for name, state in self._states.items()
        }

    async def call(
        self,
        name: str,
        query: str,
        max_results: int,
        timeout: float,
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Call one adapter. Health tracking is updated; no silent failover here."""
        from app.services.search_service import search_service

        state = self.state(name)
        if not state.enabled or not state.healthy:
            return {}, f"provider {name} disabled or unhealthy"
        try:
            payload = await asyncio.wait_for(
                search_service.search(query, max_results=max_results, provider=name),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            self.record(name, ok=False, error=f"timeout after {timeout:g}s")
            return {}, f"provider {name} timed out"
        except Exception as exc:  # pragma: no cover - defensive
            self.record(name, ok=False, error=type(exc).__name__)
            return {}, f"provider {name} failed: {type(exc).__name__}"
        error = str(payload.get("error") or "")
        ok = bool(payload.get("results")) and not error
        self.record(name, ok=ok, error=error)
        if error:
            return payload, f"provider {name}: {error[:200]}"
        return payload, None


search_provider_registry = SearchProviderRegistry()
