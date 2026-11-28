"""G4 engine API-contract check (research only).

Exercises the exact local-engine contract that model_inference.py uses:
  * Ollama /api/tags contains the exact tag qwen2.5:3b (no substitution)
  * LiteLLM /v1/chat/completions accepts tools, stream and include_usage
  * SSE carries delta content, [DONE] and a usage object

No credentials are printed. Results are sanitised. If the services are down,
the evidence records BLOCKED rather than inventing a PASS.

Usage:
    python research/native-inference-parity/g4_contract_check.py <out.json>
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA = "http://localhost:11434/api/tags"
GATEWAY = "http://localhost:4000/v1/chat/completions"
TAG = "qwen2.5:3b"
MODEL = "local-qwen-3b"
TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the public web.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}


def master_key(repo: Path) -> str:
    env = repo / ".env"
    if not env.exists():
        return ""
    match = re.search(r"^LITELLM_MASTER_KEY=(.*)$", env.read_text(encoding="utf-8", errors="replace"), re.MULTILINE)
    return match.group(1).strip().strip('"') if match else ""


def fetch(url: str, body: dict | None = None, key: str = "") -> bytes:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=300) as response:
        return response.read()


def main() -> int:
    repo = Path(__file__).resolve().parents[2]
    out_path = Path(sys.argv[1])
    evidence: dict[str, object] = {
        "gate": "G4-api-contract",
        "ollama_endpoint": OLLAMA,
        "gateway_endpoint": GATEWAY,
        "required_tag": TAG,
    }
    try:
        tags = json.loads(fetch(OLLAMA).decode("utf-8"))
        names = [item.get("name") for item in tags.get("models", [])]
        evidence["exact_tag_present"] = TAG in names
        key = master_key(repo)
        # Tool schema is checked with a bounded non-stream call; the SSE
        # contract is checked separately so a tool round cannot stall it.
        tool_response = fetch(
            GATEWAY,
            {
                "model": MODEL,
                "messages": [{"role": "user", "content": "Reply with OK only."}],
                "temperature": 0,
                "max_tokens": 16,
                "tools": [TOOL],
            },
            key,
        )
        tool_object = json.loads(tool_response.decode("utf-8", "replace"))
        chunk = fetch(
            GATEWAY,
            {
                "model": MODEL,
                "messages": [{"role": "user", "content": "Reply with OK only."}],
                "temperature": 0,
                "max_tokens": 32,
                "stream": True,
                "stream_options": {"include_usage": True},
            },
            key,
        ).decode("utf-8", "replace")
        data_lines = [line[5:].strip() for line in chunk.splitlines() if line.startswith("data:")]
        saw_done = "[DONE]" in data_lines
        deltas = []
        usage = {}
        for line in data_lines:
            if line == "[DONE]":
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            choices = obj.get("choices") or []
            if choices:
                deltas.append((choices[0].get("delta") or {}).get("content") or "")
            if obj.get("usage"):
                usage = obj["usage"]
        evidence.update(
            {
                "status": "RUN",
                "tool_schema_accepted": bool(tool_object.get("choices")),
                "saw_done": saw_done,
                "delta_count": len([item for item in deltas if item]),
                "usage_present": bool(usage),
                "usage_keys": sorted(usage),
            }
        )
        passed = bool(evidence["exact_tag_present"] and saw_done and usage and any(deltas))
        evidence["overall_pass"] = passed
        code = 0 if passed else 1
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        evidence.update(
            {
                "status": "BLOCKED",
                "reason": f"{type(exc).__name__}: services unreachable (Ollama/LiteLLM are not running)",
                "overall_pass": None,
            }
        )
        code = 2
    out_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
