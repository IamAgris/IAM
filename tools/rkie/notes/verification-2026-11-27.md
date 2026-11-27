# Verification note — 27 November 2026

Based on current working tree. Re-verify before relying on it.

## Gates run (all pass)
- `python tools/api/print_openapi.py --check` → live 801 paths / 461 schemas = snapshot; RESULT OK
- `python tools/api/check_migrations.py` → 58 numbered SQL migrations, 58 in manifest, 0 duplicate prefixes; OK
- `python -m ruff check backend` → All checks passed
- `python -m pytest backend/tests -q --no-cov` → 939 passed, 47 warnings, 5 subtests passed
- `python -m pytest backend/tests/test_hbi.py -q --no-cov` → 91 passed

## Stale claims corrected
- RKIE_CAPABILITY_AUDIT.md §18 still lists `/health/ready`, `/health/live`, `/metrics` as missing and the `{detail, code, request_id}` envelope as absent. Both are implemented: `backend/app/api/routes/ops.py` and `backend/app/core/error_response.py`, wired in `main.py`. The audit's "Done" section (line ~37) already records this; the domain table is stale.
- API snapshot drift (31 paths) is resolved: snapshot regenerated to 801/461.

## Environment
- Docker Desktop WSL engine repeatedly unresponsive in this host; `docker info` returns 500 after restarts. Code gates are runnable locally; container runtime work may require a machine reboot.
- No model API key configured; SSE chat streams a graceful offline message by design (validate with `scripts/set-model-key.ps1` when a key is available).

## Do not duplicate
- Search/memory/knowledge/RAG: see AGENTS.md §4. Repository search is `tools/rkie/`, distinct from runtime memory.
- Free sandboxes already exist (`backend/app/services/free_sandboxes/`) — simulation-lab functionality is present; do not add a second copy.
