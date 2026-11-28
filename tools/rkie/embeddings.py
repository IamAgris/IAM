#!/usr/bin/env python3
"""Optional local neural embedding adapter.

Disabled by default. When enabled, embeddings are obtained from a locally
running Ollama endpoint only — never an external provider. If the endpoint is
unavailable, callers fall back to the deterministic TF-IDF index.
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from intel_core import ROOT

CONFIG = ROOT / "tools" / "rkie" / "config" / "embeddings.json"


class EmbeddingUnavailable(RuntimeError):
    """Raised when no local embedding model is reachable."""


def config() -> dict:
    if not CONFIG.is_file():
        return {"version": 1, "enabled": False, "provider": "none"}
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def is_available(timeout: float = 10.0) -> bool:
    settings = config()
    if not settings.get("enabled"):
        return False
    if settings.get("provider") != "ollama":
        return False
    url = settings.get("base_url", "http://localhost:11434").rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def embed(text: str) -> list[float]:
    """Return a vector from the local Ollama embedding endpoint."""
    if not is_available():
        raise EmbeddingUnavailable("no enabled local embedding provider")
    settings = config()
    url = settings["base_url"].rstrip("/") + "/api/embed"
    body = json.dumps({"model": settings.get("model", "nomic-embed-text"), "input": text}).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        vector = payload["embeddings"][0]
        return [float(value) for value in vector]
    except Exception as exc:
        raise EmbeddingUnavailable(str(exc)) from exc


def main() -> int:
    print(json.dumps({
        "config": config(),
        "available": is_available(),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
