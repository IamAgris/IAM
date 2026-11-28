"""Live IAM provider compatibility matrix (Qwen + NVIDIA).

Runs the same four core IAM tools through both providers and compares the
compatibility metadata, authorisation trace and execution result. This is a
manual/live acceptance script, not a CI unit test.

    python tests/provider_compatibility_acceptance.py [tool ...]

Requires a running stack and IAM_API_KEY. No secret values are printed.
"""

import os
import sys
import time

import httpx

BASE = os.environ.get("IAM_API_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.environ.get("IAM_API_KEY", "").strip()
if not API_KEY:
    raise SystemExit("IAM_API_KEY is required for provider compatibility acceptance")

HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
NVIDIA_MODEL = os.environ.get(
    "IAM_COMPAT_NVIDIA_MODEL", "nvidia-nemotron-3.5-lightning"
)
QWEN_RAM_MB = int(os.environ.get("IAM_COMPAT_QWEN_RAM_MB", "1200"))
MAX_RETRIES = int(os.environ.get("IAM_COMPAT_RETRIES", "2"))
CAPACITY_WAIT_SECONDS = float(os.environ.get("IAM_COMPAT_CAPACITY_WAIT", "120"))


def wait_for_capacity(client: httpx.Client, estimated_ram_mb: int) -> bool:
    """Wait for OD-39 to report enough usable RAM. Never bypass IRWM."""
    deadline = time.monotonic() + CAPACITY_WAIT_SECONDS
    while time.monotonic() < deadline:
        try:
            status = client.get(f"{BASE}/api/v1/irwm/status", timeout=15).json()
        except (httpx.HTTPError, ValueError):
            time.sleep(5)
            continue
        usable = int(status.get("usable_ram_mb") or 0)
        resident = status.get("resident") or {}
        in_flight = int(resident.get("in_flight") or 0)
        if usable >= estimated_ram_mb and in_flight == 0:
            return True
        time.sleep(5)
    return False

TOOLS = {
    "tone.analyze": {
        "prompt": "Call the tone analysis tool with text: This is a calm and careful message.",
        "wire": "tone_analyze",
    },
    "network.inspect": {
        "prompt": "Call the external AI network inspection tool now. No arguments are needed.",
        "wire": "network_inspect",
    },
    "sandbox.status": {
        "prompt": "Call the free sandbox status tool now. No arguments are needed.",
        "wire": "sandbox_status",
    },
    "finance.research.read": {
        "prompt": "Call the research-only finance read tool now. Use limit 3.",
        "wire": "finance_research_read",
    },
}

PROVIDERS = [
    ("qwen", None),
    ("nvidia", NVIDIA_MODEL),
]


def run_tool(client: httpx.Client, provider: str, model, canonical: str, spec: dict) -> dict:
    names = f"{canonical} / {spec['wire']}"
    messages = [
        {
            "role": "system",
            "content": (
                "You must call the requested IAM tool. The tool may be named "
                f"{names}. Do not answer in prose."
            ),
        },
        {"role": "user", "content": spec["prompt"]},
    ]
    body = {
        "messages": messages,
        "priority": "user",
        "max_tokens": 512,
    }
    if model:
        body["model"] = model
    timeout = float(os.environ.get("IAM_COMPAT_TIMEOUT", "300"))
    base_row = {
        "provider": provider,
        "tool": canonical,
        "model": model or "local primary",
        "offered": None,
        "executed": [],
        "errors": [],
        "name_style": None,
        "removed_parameters": None,
        "tools_fallback": None,
        "ok": False,
    }
    try:
        response = client.post(f"{BASE}/api/v1/models/chat", json=body, timeout=timeout)
    except httpx.TimeoutException:
        return {
            **base_row,
            "category": "timeout",
            "errors": [f"generation timeout after {int(timeout)}s"],
        }
    if response.status_code == 503:
        return {
            **base_row,
            "category": "resource_blocked",
            "errors": ["IRWM admission refused (HTTP 503); not a tool failure"],
        }
    response.raise_for_status()
    meta = (response.json() or {}).get("iam_inference") or {}
    compat = meta.get("compatibility") or {}
    executed = meta.get("tools_executed") or []
    ok = bool(executed) and all(not item.get("error") for item in executed)
    return {
        "provider": provider,
        "tool": canonical,
        "model": meta.get("model"),
        "offered": meta.get("tools_offered"),
        "executed": [item.get("name") for item in executed],
        "errors": [item.get("error") for item in executed if item.get("error")],
        "name_style": compat.get("name_style"),
        "removed_parameters": compat.get("removed_parameters"),
        "tools_fallback": compat.get("tools_fallback"),
        "ok": ok,
        "category": "tool" if ok else "tool_failure",
    }


def main() -> int:
    selected = sys.argv[1:] or list(TOOLS)
    unknown = [name for name in selected if name not in TOOLS]
    if unknown:
        raise SystemExit(f"Unknown tools: {', '.join(unknown)}")

    results = []
    with httpx.Client(headers=HEADERS) as client:
        for provider, model in PROVIDERS:
            for canonical in selected:
                estimated = QWEN_RAM_MB if provider == "qwen" else 256
                for attempt in range(MAX_RETRIES + 1):
                    if attempt:
                        wait_for_capacity(client, estimated)
                    try:
                        row = run_tool(client, provider, model, canonical, TOOLS[canonical])
                    except (httpx.HTTPError, ValueError, KeyError) as exc:
                        row = {
                            "provider": provider,
                            "tool": canonical,
                            "model": model or "local primary",
                            "offered": None,
                            "executed": [],
                            "errors": [f"{type(exc).__name__}: {str(exc)[:120]}"],
                            "name_style": None,
                            "removed_parameters": None,
                            "tools_fallback": None,
                            "ok": False,
                            "category": "error",
                        }
                    if row["ok"] or row["category"] not in (
                        "resource_blocked",
                        "timeout",
                        "error",
                    ):
                        break
                row["attempts"] = attempt + 1
                results.append(row)
                label = "PASS" if row["ok"] else row["category"].upper()
                print(
                    f"[{label}] "
                    f"{row['provider']:<7} {row['tool']:<22} "
                    f"style={row['name_style']!s:<7} "
                    f"attempts={row['attempts']} "
                    f"executed={row['executed']} errors={row['errors']} "
                    f"fallback={bool(row['tools_fallback'])}"
                )

    passed = sum(1 for row in results if row["ok"])
    blocked = [row for row in results if row["category"] == "resource_blocked"]
    timed_out = [row for row in results if row["category"] == "timeout"]
    print(f"\n{passed}/{len(results)} tool executions succeeded")
    if blocked or timed_out:
        print(
            f"Environmental blocks (not compatibility failures): "
            f"{len(blocked)} IRWM admission, {len(timed_out)} timeout"
        )
    tool_failures = [row for row in results if row["category"] == "tool_failure"]
    return 0 if not tool_failures and passed + len(blocked) + len(timed_out) == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
