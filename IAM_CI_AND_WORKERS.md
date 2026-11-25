# CI and Background Workers

## CI

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
- `CREATOR_EMAIL_RETRY_INTERVAL_SECONDS` (default `300`)

The HTTP endpoint `POST /api/v1/creator/outbox/retry` remains available for manual
or on-demand retries.

## Docker adapter lab check

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

## Verification

- 91 unit tests pass.
- Postgres integration check passes (including a worker retry cycle).
- Docker adapter lab check passes.
- Frontend build passes with five dynamic user pages.
