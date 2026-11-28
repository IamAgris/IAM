# UWAIE Browser Substrate and Geospatial Backend — First Slice

**Status:** backend-only. At the time of this slice the frontend scope was home + suggestions; the current tree also has conversations routes. No map page was added.

Authority: `ARCHITECTURE_INDEX.md`, Doc 29 / OD-49 (`IAM_BROWSER_INTELLIGENCE_MASTER_SPEC.md`,
`IAM_BROWSER_PHASE1_IMPLEMENTATION_PLAN.md`) and Doc 16 / OD-32 (geospatial).

## WP-01 — Engine adapter registry

- `backend/app/services/browser_engine_adapters.py`: `EngineAdapter` contract,
  Chromium/Firefox/WebKit adapters, capability probing and a registry keyed by
  `uwai_browser_engine`.
- Missing runtimes raise `BrowserEngineUnavailable` — no silent fallback.
- `BrowserService` now selects the adapter instead of `getattr(playwright, engine)`.
- `BROWSER_ENABLED=false` makes construction fail closed.

## WP-02 — Session manager (first slice)

- Conservative config flags added to `backend/app/core/config.py`:
  `BROWSER_ENABLED`, `BROWSER_VISIBLE_MODE_ENABLED` (false),
  `BROWSER_ISOLATED_MODE_ENABLED` (true), `BROWSER_MAX_CONCURRENT_SESSIONS` (3),
  `BROWSER_SESSION_TTL_SECONDS` (1800), `BROWSER_PROFILE_ROOT`,
  `BROWSER_EVIDENCE_DIR`, `BROWSER_TASK_WORKER_BACKEND`.
- `BrowserService.open_session()` creates a separate context per session,
  records `owner`, `actor_type`, `permission_scope`, engine and creation time.
- Visible mode refuses without `DISPLAY` and the explicit flag. Isolated mode
  gives each session its own context (no shared cookies).
- `close_session()` tears down context, pages and tabs; `stop()` closes all
  sessions; expired sessions are reaped by TTL.
- `get_page()` remains the unchanged default-compatibility path.

## Geospatial backend rendering (no UI)

- `GET /api/v1/geo/render` returns a self-contained SVG map fragment generated
  from stored places — no external tile provider, no JavaScript, no frontend page.
- Labels are XML-escaped; coordinates use an equirectangular projection.

## Verification

- 582 unit tests pass, including adapter selection, missing-runtime denial,
  session isolation/concurrency/visible-mode refusal and SVG escaping.
- Postgres + Redis integration check exits 0 and exercises `/api/v1/geo/render`.

## WP-03 — task, evidence and attribution

The `BrowserTaskRun`, `BrowserEvidence` and `BrowserAudit` models/migration were
already present in the tree. Wired them into the API:

- `POST /api/v1/browser/tasks` accepts caller-supplied steps, verification,
  session token, actor, actor type, permission scope, mode, priority and deadline.
  It returns the Doc 29 §7.1 envelope: `task_id`, `session_id`, `status`,
  `evidence_refs`, `actor`, `actor_type`, `permission_scope`.
- `GET /api/v1/browser/tasks/{task_id}` and `.../evidence` read the persisted
  envelope and evidence package.
- `BROWSER_TASK_WORKER_BACKEND=loop` executes inline; `arq` enqueues a job.

## ARQ browser worker

- `app/workers/arq_browser_worker.py` runs `run_browser_task` with the existing
  `UWAIEService.execute()` and `BrowserEvidenceService`.
- Optional Compose service: `docker compose --profile browser-arq up -d`.

## E2E smoke and runtimes

- `tests/e2e_browser_smoke.py` is opt-in (`IAM_BROWSER_E2E=1`) and uses real
  Playwright against a public URL; skipped by default.
- Backend image now installs Chromium, Firefox and WebKit runtimes.

## Verification

- Targeted browser suites (13 tests) pass; Postgres + Redis integration exits 0.
- Full unit suite passes (637 tests). Earlier unrelated external failures in
  autonomy-graph fakes, IPLCI phase assertions and tool-authorization codes were
  resolved in the tree; no changes were needed in this browser slice.
