# Real local inference smoke — 27 November 2026

**Result: PASS.** No mocks, no paid provider, no API key.

## Request

`POST http://localhost:8080/api/v1/models/chat` (through the Caddy edge, which
reaches the backend on port 8000):

```json
{
  "messages": [{"role": "user", "content": "Reply with exactly one short sentence: what is 2+2?"}],
  "max_tokens": 32,
  "temperature": 0.1
}
```

No `model` field: the backend resolved the shared primary from config.

## Response

- HTTP 200 in **82.1 s** (CPU-only 3B cold start on the 4 vCPU core).
- `model: qwen2.5:3b`, `system_fingerprint: fp_ollama`.
- Answer: **"2+2 equals 4."**
- `finish_reason: stop`.

## Fixes needed to get here

1. OD-46 reopened to `qwen2.5:3b` in code, `.env`, Compose and LiteLLM config.
2. `timeout: 300` added to the `local-qwen-3b` entry in `infra/litellm/config.yaml`
   — LiteLLM's default 60 s cut off the first CPU-only attempt.
3. `OLLAMA_ENABLED=true` (already set locally). IRWM admitted exactly one request
   and released it in `finally`; a concurrent background request can legitimately
   hold the single slot, producing a 503 until it finishes.

## Environment caveat

Direct host access to published port 8000 timed out during this test; the same request
through Caddy on 8080 succeeded. Container health checks and inter-container traffic
were fine. This is a host/Docker networking issue, not an application failure.
