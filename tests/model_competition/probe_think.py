"""Probe whether LiteLLM passes Ollama's `think` option through for qwen3.5:4b."""

import json
import re
import urllib.request
from pathlib import Path

key = re.search(
    r"^LITELLM_MASTER_KEY=(.*)$",
    Path(".env").read_text(encoding="utf-8"),
    re.MULTILINE,
).group(1).strip().strip('"')

for extra in ({"think": False}, {"options": {"think": False}}):
    body = {
        "model": "local-qwen3.5-4b",
        "messages": [{"role": "user", "content": "Reply with exactly OK and nothing else."}],
        "max_tokens": 64,
        "temperature": 0,
        "extra_body": extra,
    }
    req = urllib.request.Request(
        "http://localhost:4000/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=240) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        choice = data["choices"][0]["message"]
        print(extra, "->", repr(choice.get("content")), "usage=", data.get("usage"))
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        print(extra, "ERROR", str(exc)[:300])
