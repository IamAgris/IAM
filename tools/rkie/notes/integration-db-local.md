# Local database integration check

**Date:** 2026-11-27 · **Based on:** working tree at commit `34d5177` plus uncommitted work

`backend/tests/integration_db_check.py` can be run locally against the running Docker
stack. It drops and recreates only the throwaway `aura_integration_test` database.

- Aura Postgres: `127.0.0.1:5434`; Aura Redis: `127.0.0.1:6381`. Ports 5432/5433
  belong to unrelated containers and will fail authentication.
- Load `POSTGRES_PASSWORD` from the repository-root `.env` (never print it) and set
  `DATABASE_URL=postgresql+asyncpg://aura:<pw>@127.0.0.1:5434/aura_integration_test`
  and `REDIS_URL=redis://127.0.0.1:6381/0` before running from `backend/`.
- The script's migration list needed `049_browser_substrate.sql` added; without it
  the browser-evidence check fails with `relation "browser_task_runs" does not exist`.

**Result:** ALL DATABASE INTEGRATION CHECKS PASSED (exit 0) — skillforge, skill runtime,
creator email, ARTEX, governance, auth/privacy, P2P/Aegis, Redis limiter, HBI and
browser task/evidence persistence.
