"""Bounded Phase-2 coding smoke test for the OD-38 model competition.

Sends one identical coding task to a model through LiteLLM, extracts the
generated Python, executes it in a temporary directory with a hard timeout,
and appends a JSON result line. This is a smoke test, not a full benchmark.

Usage:
    python tests/model_competition/smoke_coding.py [model_alias]

Default model: local-qwen-coder-3b
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENV = REPO / ".env"
RESULTS = Path(__file__).resolve().parent / "results.jsonl"
GATEWAY = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
DEFAULT_MODEL = "local-qwen-coder-3b"

TASK = (
    "Write a Python function named normalise_path(path: str) -> str that:\n"
    "1. collapses repeated '/' characters into a single '/',\n"
    "2. strips leading and trailing '/',\n"
    "3. returns '' when path is None or empty.\n"
    "Return ONLY a single fenced python code block containing the function. "
    "No explanation, no imports, no example calls."
)

ASSERTIONS = """
import importlib.util, sys
spec = importlib.util.spec_from_file_location('candidate', sys.argv[1])
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
f = mod.normalise_path
assert f(None) == '', 'None'
assert f('') == '', 'empty'
assert f('a//b///c') == 'a/b/c', 'collapse'
assert f('/x/y/') == 'x/y', 'strip'
assert f('///') == '', 'slashes only'
print('PASS')
"""


def master_key() -> str:
    text = ENV.read_text(encoding="utf-8") if ENV.exists() else ""
    match = re.search(r"^LITELLM_MASTER_KEY=(.*)$", text, re.M)
    return match.group(1).strip().strip('"') if match else ""


def extract_code(reply: str) -> str:
    match = re.search(r"```(?:python)?\s*(.*?)```", reply, re.S)
    return match.group(1).strip() if match else reply.strip()


def call_model(model: str):
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": TASK}],
            "temperature": 0,
            "max_tokens": 512,
        }
    ).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {master_key()}",
    }
    req = urllib.request.Request(
        f"{GATEWAY}/v1/chat/completions", data=payload, headers=headers
    )
    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body, (time.perf_counter() - started) * 1000


def run_candidate(code: str):
    with tempfile.TemporaryDirectory() as tmp:
        candidate = Path(tmp) / "candidate.py"
        candidate.write_text(code, encoding="utf-8")
        runner = Path(tmp) / "runner.py"
        runner.write_text(ASSERTIONS, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, str(runner), str(candidate)],
                capture_output=True,
                text=True,
                timeout=20,
                cwd=tmp,
            )
            return proc.returncode == 0 and "PASS" in proc.stdout, (
                proc.stderr.strip() or proc.stdout.strip()
            )[:500]
        except subprocess.TimeoutExpired:
            return False, "timeout after 20s"


def main() -> int:
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    try:
        body, latency_ms = call_model(model)
    except Exception as exc:  # network / gateway failure
        result = {"model": model, "passed": False, "error": str(exc)}
        print(json.dumps(result))
        RESULTS.parent.mkdir(parents=True, exist_ok=True)
        with RESULTS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(result) + "\n")
        return 1

    reply = body["choices"][0]["message"]["content"]
    code = extract_code(reply)
    passed, detail = run_candidate(code)
    result = {
        "model": model,
        "alias_returned": body.get("model"),
        "passed": passed,
        "detail": detail,
        "latency_ms": round(latency_ms, 1),
        "usage": body.get("usage", {}),
        "code_chars": len(code),
        "code": code[:1000],
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result) + "\n")
    print(json.dumps(result, indent=2))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
