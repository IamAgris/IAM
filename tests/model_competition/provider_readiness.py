"""Report which LiteLLM aliases are actually callable, not merely listed.

Listing an alias in infra/litellm/config.yaml does not mean a provider can be
called: hosted entries need credentials. This script checks credentials in
.env and Ollama reachability, then prints a readiness table and writes JSON.

Usage: python tests/model_competition/provider_readiness.py
"""

import json
import re
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENV = REPO / ".env"
OUT = Path(__file__).resolve().parent / "results" / "provider_readiness.json"
OLLAMA = "http://localhost:11434/api/tags"

ALIASES = [
    ("nvidia-llama-3.3-70b", "NVIDIA_API_KEY"),
    ("nvidia-qwen-2.5-72b", "NVIDIA_API_KEY"),
    ("nvidia-deepseek-r1", "NVIDIA_API_KEY"),
    ("nvidia-nemotron", "NVIDIA_API_KEY"),
    ("qwen3.5-9b", "DASHSCOPE_API_KEY"),
    ("gemini-free (template, disabled)", "GOOGLE_API_KEY"),
    ("gpt-4o-mini", "OPENAI_API_KEY"),
    ("claude-3-haiku", "ANTHROPIC_API_KEY"),
    ("local-qwen-coder-3b", None),
    ("local-qwen-3b", None),
    ("local-qwen3.5-4b", None),
]


def env_values() -> dict:
    text = ENV.read_text(encoding="utf-8") if ENV.exists() else ""
    values = {}
    for match in re.finditer(r"^([A-Z][A-Z0-9_]*)=(.*)$", text, re.M):
        values[match.group(1)] = match.group(2).strip().strip('"')
    return values


def ollama_reachable() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> None:
    values = env_values()
    online = ollama_reachable()
    rows = []
    for alias, key in ALIASES:
        if key is None:
            status = "READY" if online else "OFFLINE (Ollama unreachable)"
        elif not values.get(key):
            status = f"NO KEY ({key})"
        else:
            status = "READY (credentials present — call not yet probed)"
        rows.append({"alias": alias, "status": status})

    print(f"{'alias':38} status")
    print("-" * 78)
    for row in rows:
        print(f"{row['alias']:38} {row['status']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps({"ollama_reachable": online, "aliases": rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
