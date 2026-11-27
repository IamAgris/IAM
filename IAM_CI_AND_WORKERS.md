# CI and Background Workers

## CI

Run the exact local equivalent with `./scripts/ci_local.ps1` (needs the Compose
Postgres + Redis services). It compiles the backend, runs all unit tests, runs
the Postgres/Redis integration check, then builds the frontend.

`.github/workflows/ci.yml` runs three jobs on push and pull request:

1. **backend-unit** — installs `backend[dev]`, compiles `backend/app`, runs all
   `unittest` tests.
2. **backend-integration** — starts a `pgvector/pgvector:pg17` service, then runs
   `backend/tests/integration_db_check.py` against a throwaway database. Migrations
   `001`–`009` are applied and all lifecycles are exercised.
3. **frontend** — `npm ci` and `npm run build` in `frontend/`.

CI does not run the Docker adapter lab check because it depends on a local image
and Docker daemon.

## Creator email retry worker

`backend/app/workers/creator_email_worker.py` calls
`CreatorApprovalService.retry_failed_deliveries()` on an async interval. It is
started and stopped in the backend lifespan. It only retries delivery — it never
creates or changes approval authority.

Configuration:

- `CREATOR_EMAIL_WORKER_ENABLED` (default `true`)
- `CREATOR_EMAIL_WORKER_BACKEND` (`loop` default, or `arq` for OD-08)
- `CREATOR_EMAIL_RETRY_INTERVAL_SECONDS` (default `300`)

The ARQ worker is `app/workers/arq_creator_email.py`; run it separately with
`docker compose --profile arq up -d` or `arq app.workers.arq_creator_email.WorkerSettings`.

After `CREATOR_EMAIL_MAX_ATTEMPTS` failures, delivery is moved to
`creator_email_dead_letters`, retried no further, logged as an error, and optionally
reported to `CREATOR_ALERT_WEBHOOK_URL`. Inspect with
`GET /api/v1/creator/outbox/dead-letters`. An operator can resolve an item with
`POST /api/v1/creator/outbox/dead-letters/{request_id}/resolve`, which clears the
dead letter and immediately re-queues delivery. `POST /api/v1/creator/outbox/retry`
retries all non-dead-lettered entries.

## Docker adapter lab check

The opt-in real browser smoke also passed:

```bash
cd backend
IAM_BROWSER_E2E=1 python tests/e2e_browser_smoke.py
```

It navigated to `https://example.com` with real Playwright and returned the
expected title and page excerpt.

`backend/tests/docker_adapter_lab_check.py` is a manual script:

```bash
cd backend
python tests/docker_adapter_lab_check.py
```

It runs two real scripts in a disposable container using
`project-aura-backend:latest` by default (override with `SKILL_RUNTIME_TEST_IMAGE`).
It verifies both that a script executes and that an outbound TCP connection is
blocked by `--network none`.

Result: `IAM_RUNTIME_LAB_OK` printed, `NETWORK_BLOCKED` printed.

## Browser task worker (Doc 29 / OD-49)

`backend/app/workers/arq_browser_worker.py` executes queued UWAIE tasks under OD-08. It checks
the run's terminal state before execution (`job_id=task_id` gives idempotency), enforces the
deadline, and records failures with a bounded retry count. Failed external actions are never
silently replayed.

```bash
docker compose --profile browser-arq up -d        # browser-task-worker
```

Set `BROWSER_TASK_WORKER_BACKEND=arq` to queue through ARQ; the default `loop` backend executes
through `POST /api/v1/browser/tasks` inline. The browser API is admin-scoped
(`/api/v1/browser` in `auth_policy.py`).

Local OCR is provided by `pytesseract` plus the `tesseract-ocr` packages installed in the image.
It is opt-in via `BROWSER_OCR_ENABLED` (default `false`). When enabled, page understanding reports
`ocr.available`; a missing library or binary produces `{available: false, reason}`, never empty
text presented as a successful OCR pass. The Windows host has the Python binding but no Tesseract
binary, so OCR there reports unavailable until a binary is installed; rebuild the image for the
container path.

## Live browser smoke (opt-in)

`tests/browser_substrate_smoke.py` is a live-stack smoke test, not a CI gate:

```powershell
$env:IAM_BROWSER_SMOKE = "1"
python tests/browser_substrate_smoke.py
```

It opens a headless session, navigates to a public page through `/api/v1/browser`, checks the
task ID, evidence refs and attribution, confirms a CAPTCHA target is rejected, and closes the
session. Success prints `IAM_BROWSER_P1_OK`; skipped runs print `SKIPPED` and never count as a
pass. `IAM_API_KEY` and an admin-scoped credential are required.

## Verification

- Backend unit suite passes (662 tests at the time of this update).
- Browser evidence/API/worker tests pass; ruff clean on Doc 29 files.
- Postgres integration check passes (including browser run/evidence persistence).
- Docker adapter lab check passes.
- Frontend build passes with five dynamic user pages.
