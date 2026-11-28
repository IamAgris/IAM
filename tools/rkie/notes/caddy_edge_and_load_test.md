# Caddy edge + concurrent load test (Doc 21 / OD-37)

**Date:** 27 November 2026 · **Based on:** current working tree; verified with
`Search-IAMRepo.ps1 -Query caddy -Mode auto` (spec references only, no implementation) and
`-Query load_test -Mode files` (no results) before adding code.

## Files

| File | Role |
|------|------|
| `infra/caddy/Caddyfile` | HTTP :8080 edge; `/api/*` and `/health` → backend:8000, rest → frontend:3000; `flush_interval -1` for SSE |
| `docker-compose.yml` | Optional `caddy` service behind Compose profile `edge`; volumes `aura_caddy_data`, `aura_caddy_config` |
| `tests/load_test.py` | 50 concurrent sessions × 2 messages; measures p50/p95/p99, errors |
| `tests/results/load_test.json` | Evidence output (overwritten each run) |
| `docs/IAM_OPEN_SPECS_RESOLVED.md` | Implementation note appended to open spec E |

## Run

```powershell
docker compose --profile edge up -d --wait caddy
$env:IAM_LOAD_BASE_URL='http://localhost:8080'
python tests/load_test.py
```

The edge is opt-in: the default `docker compose up -d` does not start Caddy.

## Verified result (27 Nov 2026, through Caddy)

- Proxy: `/health` 200, `/` 200, `/api/v1/openapi.json` 200 via port 8080.
- Load: 50/50 sessions, 150 requests, 0 errors, p50 736 ms, p95 2427 ms, p99 2486 ms — passes
  the 5000 ms target from `docs/IAM_OPEN_SPECS_RESOLVED.md` §E.

## Boundary

Caddy is transport only. No authority, signing or decision logic runs at the edge, and the
load test never calls paid providers or high-impact endpoints.
