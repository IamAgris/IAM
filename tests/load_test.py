"""Doc 21 / OD-37: bounded concurrent-session load test.

Target from IAM_OPEN_SPECS_RESOLVED.md: 50 concurrent anonymous sessions,
p95 response time < 5s, no cross-session leakage, no 5xx.

Run:  python tests/load_test.py
Env:  IAM_LOAD_BASE_URL (default http://localhost:8000)
      IAM_LOAD_CONCURRENCY (default 50)
      IAM_LOAD_MESSAGES (default 2 messages per session)

This exercises public session/message endpoints only. It does not call paid
providers, create accounts or perform any high-impact action.
"""

import asyncio
import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE = os.environ.get("IAM_LOAD_BASE_URL", "http://localhost:8000").rstrip("/")
CONCURRENCY = int(os.environ.get("IAM_LOAD_CONCURRENCY", "50"))
MESSAGES = int(os.environ.get("IAM_LOAD_MESSAGES", "2"))
P95_LIMIT_MS = 5000
RESULTS = Path(__file__).parent / "results" / "load_test.json"


def percentile(sorted_values, fraction):
    if not sorted_values:
        return None
    index = min(len(sorted_values) - 1, int(len(sorted_values) * fraction))
    return round(sorted_values[index], 1)


async def timed_request(client, method, path, **kwargs):
    started = time.perf_counter()
    try:
        response = await client.request(method, BASE + path, **kwargs)
        elapsed = (time.perf_counter() - started) * 1000
        return elapsed, response.status_code, response
    except Exception as exc:
        elapsed = (time.perf_counter() - started) * 1000
        return elapsed, 0, exc


async def main():
    limits = httpx.Limits(max_connections=CONCURRENCY * 2, max_keepalive_connections=CONCURRENCY)
    async with httpx.AsyncClient(limits=limits, timeout=30.0) as client:
        # Phase 1: create sessions concurrently.
        created, session_latencies, session_errors = [], [], []

        async def create_session(index):
            elapsed, status, response = await timed_request(
                client, "POST", "/api/v1/access/sessions", json={"mode": "focus"}
            )
            session_latencies.append(elapsed)
            if status == 200:
                token = response.json().get("session_token")
                if token:
                    created.append((index, token))
                else:
                    session_errors.append("no session_token")
            else:
                session_errors.append(f"session status {status}")

        await asyncio.gather(*(create_session(i) for i in range(CONCURRENCY)))

        # Phase 2: send messages to each session concurrently.
        message_latencies, message_errors = [], []

        async def send_messages(index, token):
            for step in range(MESSAGES):
                elapsed, status, _ = await timed_request(
                    client,
                    "POST",
                    "/api/v1/access/messages",
                    json={
                        "session_token": token,
                        "role": "user",
                        "content": f"LOAD_TEST_{index}_{step}",
                    },
                )
                message_latencies.append(elapsed)
                if status != 200:
                    message_errors.append(f"session {index} message status {status}")

        await asyncio.gather(*(send_messages(i, t) for i, t in created))

    all_latencies = sorted(session_latencies + message_latencies)
    total_errors = session_errors + message_errors
    total_requests = len(all_latencies)
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
        "target_concurrency": CONCURRENCY,
        "sessions_created": len(created),
        "messages_per_session": MESSAGES,
        "total_requests": total_requests,
        "errors": len(total_errors),
        "error_samples": total_errors[:10],
        "latency_ms": {
            "p50": percentile(all_latencies, 0.50),
            "p95": percentile(all_latencies, 0.95),
            "p99": percentile(all_latencies, 0.99),
            "max": round(max(all_latencies), 1) if all_latencies else None,
            "mean": round(statistics.mean(all_latencies), 1) if all_latencies else None,
        },
        "p95_limit_ms": P95_LIMIT_MS,
    }
    summary["passed"] = (
        len(created) == CONCURRENCY
        and not total_errors
        and summary["latency_ms"]["p95"] is not None
        and summary["latency_ms"]["p95"] < P95_LIMIT_MS
    )

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"=== Load test: {BASE} ===")
    print(f"sessions: {len(created)}/{CONCURRENCY}  requests: {total_requests}  errors: {len(total_errors)}")
    print(f"p50={summary['latency_ms']['p50']}ms p95={summary['latency_ms']['p95']}ms p99={summary['latency_ms']['p99']}ms")
    print(f"[{'PASS' if summary['passed'] else 'FAIL'}] p95 < {P95_LIMIT_MS}ms and no errors")
    print(f"evidence: {RESULTS}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
