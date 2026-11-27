"""Ambient governance context propagation (P6).

A single boundary — an HTTP request or an agent session — establishes the
context once. Every downstream call, including legacy code that does not pass
an explicit ``governance_context`` argument, inherits it. Explicit values win
over ambient ones, and an absent context remains absent (no silent approval).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar, Token
from typing import Any, AsyncIterator, Dict, Mapping, Optional

_current: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "iplci_governance_context", default=None
)


def set_governance_context(
    context: Optional[Mapping[str, Any]],
) -> Optional[Token[Dict[str, Any]]]:
    """Set the ambient context and return a token for ``reset_governance_context``."""
    value = dict(context) if context else None
    if not value or not value.get("source_id"):
        return None
    return _current.set(value)  # type: ignore[return-value]


def reset_governance_context(token: Optional[Token[Dict[str, Any]]]) -> None:
    if token is not None:
        _current.reset(token)  # type: ignore[arg-type]


@asynccontextmanager
async def governance_context(context: Optional[Mapping[str, Any]]) -> AsyncIterator[None]:
    """Scope an ambient governance context to one request or agent step."""
    token = set_governance_context(context)
    try:
        yield
    finally:
        reset_governance_context(token)


def get_governance_context() -> Optional[Dict[str, Any]]:
    value = _current.get()
    return dict(value) if value else None


def resolve_governance_context(
    explicit: Optional[Mapping[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Merge an explicit context over the ambient one; never invent a source."""
    ambient = get_governance_context() or {}
    direct = {
        key: value for key, value in dict(explicit or {}).items() if value is not None
    }
    merged = {**ambient, **direct}
    return merged if merged.get("source_id") else None
