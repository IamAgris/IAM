# IAM — Browser Architecture Phase 1 Implementation Plan

**Document:** 29a — companion implementation plan to Document 29 (`IAM_BROWSER_INTELLIGENCE_MASTER_SPEC.md`)  
**Version:** 1.0 · 27 November 2026  
**Status:** **PLAN + WP-03 implementation record.** The plan itself makes no change; WP-03 was implemented separately and is recorded in §9. WP-01 and WP-02 were implemented by a concurrent process (not by this document).  
**Authority:** Doc 29 / OD-49 (confirmed 27 November 2026). Extends OD-27 UWAIE; does not reopen or alter any locked decision.  
**Scope:** Phase 1 only of Doc 29 §11. Phases 2–8 remain specified but unstarted.  
**Method:** evidence-based. Every "covered / partial / absent" statement below is backed by a file and line reference in the current working tree. Claims in `README.md` are treated as claims, not evidence.

---

## 1. Purpose and constraints

Doc 29 §11 defines P1 as:

> Core browser substrate: engine adapters, Playwright controller, visible/headless/isolated modes, session manager, browser API skeleton, ARQ task queue. Exit: navigate and interact on a public site with task ID, evidence and attribution.

This plan closes the gap between that definition and the current tree. It follows the repository contract in `AGENTS.md`:

- **Extend, do not duplicate.** `browser_service.py`, `uwaie_service.py`, `internetaccess_service.py`, `autonomous_web_task_service.py` and the existing API routes are the browser stack. No second browser implementation, no second search/memory/knowledge system.
- **Model RAM (OD-39) governs models, not browser sessions.** Browser concurrency needs its own enforced cap; DB fields alone are not enforcement.
- **No assumption that a claim is operational.** Where the README says browser automation is implemented, code evidence confirms only part of it.
- **Fail closed.** Missing runtime, missing approval or missing evidence is a denial, not a silent fallback.

### 1.1 Open Phase 0 evidence item

Doc 29 §11 P0 exit is "signed decision recorded". OD-49 is recorded in `IAM_OWNER_DECISIONS.md`, `ARCHITECTURE_INDEX.md` and Doc 29, but **no OD-03/OD-42 hardware-signed decision artefact exists in the tree**. P0 must not be marked complete until the signed decision record is stored by the Creator's signing path. This plan does not manufacture that evidence.

---

## 2. Evidence baseline — what actually exists

| Area | Status | Evidence |
|------|--------|----------|
| Playwright controller | **Covered** | `backend/app/services/browser_service.py` L13 async Playwright import, L67–92 launch, L120–423 fetch/interact/search; `playwright>=1.48.0` in `backend/pyproject.toml` L25, pinned `1.65.2` in `backend/requirements.lock.txt` L74; `backend/Dockerfile` L40 `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright` |
| Headless mode | **Covered** | `browser_service.py` L30/L77 `headless=True` default |
| Core interactions | **Covered** | `browser_service.py` `interact()` L227–347: navigate, click, fill, submit, scroll, screenshot, text, url, links, upload, download, tabs; bounded transfer path L104–111 |
| Engine allowlist | **Partial** | `browser_service.py` L26 `ENGINE_ALLOWLIST`, L36–38 config selection, L75 `getattr(playwright, engine)` — one controller with an engine name; no adapter interface, no capability negotiation. `Dockerfile` L43 `playwright install chromium || true` — Firefox/WebKit runtimes are **not** installed |
| Multi-tab | **Covered** | `browser_service.py` L46–47, L193–215 |
| UWAIE lifecycle, permissions, verification, handover | **Covered** | `backend/app/services/uwaie_service.py` L69–217, L331–411; `backend/app/api/routes/uwaie.py` L55–135; semantic `INSPECT_SCRIPT` L34–53 (no fixed coordinates) |
| Internet permissions and sessions | **Covered** | `backend/app/services/internetaccess_service.py` L36–94 (13 gates), L96–165; `backend/app/api/routes/internetaccess.py` L71–215 |
| Credential vault | **Covered** | `backend/app/services/website_credentials.py` L33–139 AES-GCM + signed reveal/rotate; `backend/app/api/routes/websitecredentials.py` L34–96 |
| Visible mode | **Absent at runtime** | `browser_service.py` L30 headless only; "visible" exists only as DB enum in `backend/app/services/browser_infrastructure_service.py` L54 and `backend/app/models/web_knowledge.py` L246. No launch path uses it |
| Isolated mode | **Absent** | `browser_service.py` L88 creates **one shared `BrowserContext`**; L46–47 pages/tabs are keyed by token but share cookies/profile. Config comment `config.py` L177 says "all sessions isolated" — code does not implement it |
| Session manager | **Partial** | in-memory `_pages`/`_tabs` L46–47 + DB `InternetSession` `internetaccess_service.py` L96–122 + `UWAIEService.create_session()` L65–67; no profiles, expiry/reaping, owner/scope on runtime session, cross-process persistence |
| Browser API contract (`iam.browser.*`) | **Absent in spec form** | many real routes exist (`/api/v1/uwaie/*`, `/api/v1/web/*`, `/api/v1/internet/*`, `/api/v1/research/*`) but none returns Doc 29 §7.1 envelope `task_id / session_id / status / evidence_refs` |
| ARQ task queue | **Absent** | `backend/app/workers/arq_creator_email.py` L24–26 is the only ARQ worker; no `enqueue_job` call in `backend/app`; `AutonomousWebTask` rows have timestamps hardcoded `None` (`autonomous_web_task_service.py` L83–86/L173) and no consumer |
| Task ID / attribution contract | **Absent** | `browser_service.interact()` L278–284 and `uwaie_service.execute()` L210–217 do not propagate `task_id`; `actor` is captured by routes (e.g. `uwaie.py` L50–52) into `AuditEvent` but there is no agent-vs-Creator field or permission scope on browser actions |
| Evidence package | **Partial** | `AuditEvent` rows + base64 screenshot in `browser_service.py` L307–311; no `browser_evidence` table, no evidence_id/hash/timestamp_ms/source metadata package, no append-only `browser_audit` |
| Browser resource limits | **Partial** | `BrowserInfrastructure.concurrent_session_limit` is DB-only; `backend/app/services/irwm.py` L67–142 enforces **model** RAM and is never called by browsing |
| Tests | **Partial** | `backend/tests/test_phase9_conformance.py` L178–234, `test_web_knowledge.py` L371, `test_digital_access.py`, `tests/uwaie_storage_smoke.py` (live smoke, skips without `IAM_API_KEY`). All browser-page tests use mocks; **no real Playwright E2E test** |

**Conclusion:** the controller, headless interaction, permission gates, credential vault and UWAIE lifecycle are real. The adapter abstraction, visible/isolated runtime, full session manager, browser ARQ queue and the task/evidence/attribution data contract are not. P1 is a gap-closure and verification programme, not a rewrite.

---

## 3. Phase 1 scope and non-goals

### 3.1 In scope

1. Engine adapter registry with capability negotiation and fail-closed missing runtimes.
2. Per-session browser contexts with three launch modes (headless, visible, isolated).
3. Runtime session manager with owner, permission scope, expiry and cleanup.
4. Standard `iam.browser.*` API envelope over existing services.
5. ARQ-backed browser task queue with priorities, retries, deadlines and cancellation.
6. `task_id` / `evidence_refs` / actor-attribution data contract and persistence.
7. Tests and an opt-in live public-site smoke test.

### 3.2 Explicitly out of scope

TIPS/Tor (P5–P6), DOM/visual intelligence and OCR (P2), legal gateway and governed knowledge writes (P4), autonomous step generation, multi-agent scheduling (P7), full lifecycle/patching (P8), any new hosted dependency, any change to identity/signing/finance/protected core, and any new top-level system.

---

## 4. Work packages

### WP-01 — Engine adapter registry and capability negotiation

**Objective:** replace the single `getattr(self._playwright, self.engine)` switch with a small adapter contract while preserving the existing public API.

**Files:** modify `backend/app/services/browser_service.py` (L26–38, L67–92); add `backend/app/services/browser_engine_adapters.py`.

**Design:**
- `EngineAdapter` protocol: `name`, `capabilities()`, `launch(headless, **kwargs)`, `new_context(**kwargs)`.
- `ChromiumAdapter`, `FirefoxAdapter`, `WebKitAdapter` wrap the existing Playwright engine names; no new dependency.
- Registry keyed by the existing `ENGINE_ALLOWLIST`; `settings.uwai_browser_engine` remains the default.
- Capability probe before launch: if the engine runtime is not installed, raise a typed `BrowserEngineUnavailable` error with a precise message — never silently fall back to Chromium.
- Keep `_ensure_browser()` restart logic (L49–65) working across adapters.

**Tests:** extend `backend/tests/test_phase9_conformance.py` `BrowserAutomationTests` (L178–234) with adapter selection, allowlist rejection and missing-runtime fail-closed cases.

**Exit:** all three adapters selectable through the registry; missing runtime denies; existing browser tests pass unchanged.

---

### WP-02 — Per-session contexts and three launch modes

**Objective:** implement the isolation that `config.py` L177 currently claims.

**Files:** modify `backend/app/services/browser_service.py` (L28–47, L67–92, L113–118, L219–225); modify `backend/app/core/config.py` (L177–183); add tests.

**Design:**
- Replace the single shared `_context` with `_contexts: dict[session_token, BrowserContext]`; keep `get_page()` as a compatibility shim that uses a default context.
- Add `session.open(mode, profile, scope, owner)` returning `{session_id, mode, engine}`. Modes:
  - `headless` — current default, unchanged behaviour;
  - `visible` — `headless=False`, refused unless `DISPLAY` is present **and** `settings.browser_visible_mode_enabled=True` (default false);
  - `isolated` — fresh context, disposable profile directory under a configured root, no cookie sharing, destroyed on close.
- Add `session.close(session_id)` with context/page/tab teardown and profile cleanup; add expiry/reaping driven by `settings.browser_session_ttl_seconds`.
- Record `owner`, `actor_type` (`agent` | `creator`) and `permission_scope` on each runtime session; link to DB `InternetSession` rather than replacing it.
- New config flags (defaults conservative):
  - `browser_enabled: bool = True`
  - `browser_visible_mode_enabled: bool = False`
  - `browser_isolated_mode_enabled: bool = True`
  - `browser_max_concurrent_sessions: int = 3` (bounded; IRWM unaffected)
  - `browser_session_ttl_seconds: int = 1800`
  - `browser_profile_root: str = ""` (empty → temp dir)
  - `browser_evidence_dir: str = ""` (empty → temp dir)
  - `browser_task_worker_backend: str = "loop"` (`loop` | `arq`, mirrors Creator email worker pattern)

**Tests:** new `backend/tests/test_browser_sessions.py` — context separation (no shared cookies), visible-mode refusal without display/flag, isolated cleanup, TTL reaping, concurrency cap, shutdown teardown.

**Exit:** sessions demonstrably isolated; visible mode fails closed; headless behaviour unchanged.

---

### WP-03 — Task, evidence and attribution contract

**Objective:** make Doc 29 §7.1/§7.2 enforceable rather than aspirational.

**Files:** add `backend/app/services/browser_evidence_service.py`; modify `backend/app/services/autonomous_web_task_service.py` (L37–96, L115, L147, L164) and `backend/app/services/uwaie_service.py` (L106–217); add models to `backend/app/models/web_knowledge.py` alongside `AutonomousWebTask` (L195) and `BrowserInfrastructure` (L237); add migration `backend/app/db/migrations/049_browser_substrate.sql` and append sequence **49**, number **49** to `backend/app/db/migrations/MIGRATION_ORDER.json`. Numbers 047 and 048 were taken concurrently by IPLCI migrations — do not renumber existing entries.

**Logical tables (new, not replacements):**
- `browser_task_runs` — `task_id`, `session_id`, `owner`, `actor`, `actor_type`, `permission_scope`, `mode`, `engine`, `state` (`queued|running|awaiting_approval|verifying|completed|failed|cancelled|timed_out`), `priority`, `deadline`, `retries`, `started_at`, `finished_at`, `result_ref`.
- `browser_evidence` — `evidence_id`, `task_id`, `url`, `screenshot_ref`, `excerpt`, `timestamp_ms`, `source_metadata`, `sha256`, `retention_until`.
- `browser_audit` — append-only: `event_id`, `task_id`, `actor`, `actor_type`, `action`, `target`, `outcome`, `timestamp_ms`; no secret values.

**Contract:** every browser operation returns `{task_id, session_id, status, evidence_refs, actor, permission_scope}`; `status` reflects **verified** outcome, never an assumed success. Redact credentials in evidence and logs by reusing the existing redaction behaviour in `uwaie_service.py` L203–207.

**Tests:** `backend/tests/test_browser_evidence.py` — evidence package completeness, hash integrity, redaction, append-only audit, no false success claim; extend `backend/tests/integration_db_check.py` with the new tables.

**Exit:** a task can be traced from request → session → action → evidence → verified result; secrets absent from logs and evidence.

---

### WP-04 — ARQ browser task queue

**Objective:** make `AutonomousWebTask` executable and cancellable using the locked OD-08 runtime.

**Files:** add `backend/app/workers/arq_browser.py` (mirror `backend/app/workers/arq_creator_email.py` L17–29); modify `backend/app/services/autonomous_web_task_service.py`; modify `backend/app/core/config.py`; modify `docker-compose.yml` ARQ profile if a second worker process is required.

**Design:**
- `WorkerSettings.functions = [execute_browser_task]`, `RedisSettings.from_dsn(settings.redis_url)`, explicit `job_timeout`, `max_jobs`.
- `AutonomousWebTaskService.create()` enqueues when `browser_task_worker_backend="arq"`; `loop` mode runs an in-process bounded worker (same pattern as Creator email worker) so local-first deployments work without Redis.
- Worker loads the task record, opens/attaches a session by `session_id`, executes steps through `uwaie_service.execute()`, verifies, records evidence, then writes real `started_at`/`completed_at` (replacing the hardcoded `None` at L83–86/L173).
- Support `cancel` (task state + browser session close), deadline, bounded retry with backoff, and idempotency key from `task_id`.
- No CAPTCHA/paywall circumvention: retain `BLOCKED_TARGETS` and handover in `uwaie_service.py` L28–31/L191–193.

**Tests:** `backend/tests/test_browser_task_queue.py` — enqueue, status transitions, retry bound, deadline, cancellation, loop-mode execution with mocked browser; verify no worker touches Tor or private networks.

**Exit:** a queued task executes end-to-end in loop mode; ARQ mode is wired and documented but need not be running in CI.

---

### WP-05 — `iam.browser.*` API envelope over existing routes

**Objective:** provide the single integration surface mandated by Doc 29 §7 without reimplementing browser logic.

**Files:** add `backend/app/api/routes/browser_api.py` (prefix `/api/v1/browser`); register in `backend/app/main.py` beside the existing UWAIE/internet routes (current registrations around L193–244); update `IAM_OPENAPI.json` via `python tools/api/print_openapi.py` (regenerate, never hand-edit) and `backend/app/core/auth_policy.py` scopes as needed.

**Endpoints (thin adapters):**

| Endpoint | Delegates to | Returns |
|----------|--------------|---------|
| `POST /sessions` | `BrowserService.session.open`, `InternetAccessService.create_session` | session envelope |
| `DELETE /sessions/{id}` | `BrowserService.session.close` | closed status |
| `POST /tasks` | `AutonomousWebTaskService.create` (+ WP-04 enqueue) | task envelope |
| `GET /tasks/{id}` | task record | state, actor, scope |
| `POST /tasks/{id}/cancel` | WP-04 cancel | cancelled status |
| `GET /tasks/{id}/evidence` | `BrowserEvidenceService` | evidence package |
| `POST /inspect` | `UWAIEService.inspect` | semantic DOM snapshot + evidence refs |
| `POST /execute` | `UWAIEService.execute` | verified result + evidence refs |
| `POST /verify` | `UWAIEService._verify` via public method | verification result |

All responses use the WP-03 envelope. Authorised subsystems and the primary model call this API; they do not import `BrowserService` directly.

**Tests:** `backend/tests/test_browser_api.py` — envelope shape, auth scopes, delegation (no duplicate logic), error taxonomy.

**Exit:** OpenAPI drift check passes; existing routes remain functional; no second browser stack introduced.

---

### WP-06 — Live public-site smoke test (opt-in)

**Objective:** satisfy the P1 exit criterion with real browser evidence, without making CI depend on a browser runtime.

**Files:** add `tests/browser_substrate_smoke.py`, following the skip pattern of `tests/uwaie_storage_smoke.py` (L28–30).

**Design:**
- Skips unless `IAM_BROWSER_SMOKE=1` **and** a browser executable is available; never silently "passes" when skipped.
- Navigate to a public page (default `https://example.com`, configurable), interact (click/text extraction), verify expected content, persist evidence and assert `task_id`, `evidence_refs`, `actor`.
- Assert no private-network target, no credential access, and that a deliberately blocked target (CAPTCHA pattern) is rejected with handover rather than executed.

**Exit:** smoke printed `IAM_BROWSER_P1_OK` with evidence IDs; skipped runs explicitly report `SKIPPED`, never `PASS`.

---

### WP-07 — Verification gates and documentation

**Files:** update `IAM_CI_AND_WORKERS.md`, `.github/workflows/ci.yml` (add unit tests only; do not add live browser to CI), `IAM_API_CONTRACTS.md`, `IAM_DATABASE_INTEGRATION_REPORT.md`, and add a short note under `tools/rkie/notes/`.

**Gates (from `AGENTS.md` §3):**
```powershell
python tools/api/print_openapi.py --check
python tools/api/check_migrations.py
python -m ruff check backend
python -m pytest backend/tests -q --cov=app --cov-fail-under=60
```
Plus `backend/tests/integration_db_check.py` against a throwaway database, and the opt-in smoke from WP-06.

**Exit:** all gates pass; phase status recorded in Doc 29 §11 as `P1 COMPLETE` with evidence references — not before.

---

## 5. Dependency order

```
WP-01 (adapters) ─┬─> WP-02 (sessions) ─┬─> WP-03 (contract/evidence)
                  │                      │
                  └──────────────────────┴─> WP-04 (queue) ─> WP-05 (API)
                                                                  │
                                                                  v
                                                    WP-06 (live smoke) ─> WP-07 (gates/docs)
```

WP-03's migration must land before WP-04/05 code that writes task runs or evidence. WP-06 must not run until WP-01–05 are complete.

---

## 6. Phase 1 exit checklist

| # | Criterion (Doc 29 §11 P1) | Evidence required |
|---|---------------------------|-------------------|
| 1 | Engine adapters | WP-01 registry tests; missing-runtime denial |
| 2 | Playwright controller | existing controller preserved; no regression in `test_phase9_conformance.py` |
| 3 | Visible / headless / isolated modes | WP-02 tests; visible refused without flag/display |
| 4 | Session manager | per-session contexts, owner/scope, TTL, cleanup |
| 5 | Browser API skeleton | WP-05 envelope; OpenAPI drift check passes |
| 6 | ARQ task queue | WP-04 enqueue/status/cancel/retry/deadline |
| 7 | Navigate + interact on public site | WP-06 smoke with `IAM_BROWSER_P1_OK` |
| 8 | Task ID, evidence, attribution | WP-03 records; redaction verified |
| 9 | No false success | verification gate asserted in WP-03/WP-06 |
| 10 | No scope creep | no Tor, no P2+ code, no new top-level system, no new dependency |

P1 is **not** complete if any row lacks evidence. Skipped smoke tests do not satisfy row 7.

---

## 7. Decisions and risks requiring owner/operator input

| Item | Why it matters | Recommended default |
|------|----------------|---------------------|
| Signed OD-49 decision artefact (§1.1) | P0 exit not yet evidenced under OD-03/OD-42 | Creator signs and stores record before P1 is marked complete |
| Visible mode deployment | Needs `DISPLAY`/Xvfb or remote desktop; not present in current Compose | Keep disabled by default; enable only in an operator-approved profile |
| Firefox / WebKit runtimes | `Dockerfile` L43 installs Chromium best-effort only | Adapter fails closed; install runtimes only when compatibility testing is required |
| Per-session context memory | Multiple contexts increase RAM; OD-39 protects core services | Cap at 3 sessions, TTL 30 min, no pooling with model RAM |
| ARQ worker process | Second worker in Compose profile; Redis already present | `loop` backend default; `arq` opt-in for deployed stacks |
| Evidence storage and retention | Screenshots/excerpts can contain personal data | Local configured root, hashed, redacted, retention expiry, deletion path |

---

## 8. Statement of status

This document is a plan. Implementation status is recorded separately in §9. No migration has been applied to a running database, no browser mode has been enabled at deployment, and no worker has been started by this document. The evidence baseline in §2 describes the tree at the time of the audit.

---

## 9. Implementation record (27 November 2026)

### 9.1 WP-01 and WP-02 — concurrent implementation

Implemented outside this work session while the plan was being written:

- `backend/app/services/browser_engine_adapters.py` — adapter registry, capability probe, `BrowserEngineUnavailable` fail-closed behaviour.
- `backend/tests/test_browser_engine_adapters.py` — adapter and session tests.
- `backend/app/core/config.py` L190–197 — `browser_enabled`, visible/isolated mode flags, concurrency cap, TTL, profile/evidence roots, worker backend.
- `backend/app/services/browser_service.py` — adapter use and per-session `_contexts` / `open_session` / `close_session`.

These are **recorded as implemented by another process**, not as work of this plan. No file in this group was edited here.

### 9.2 WP-03 — implemented in this session

| Change | File |
|--------|------|
| Evidence/task/audit models (`BrowserTaskRun`, `BrowserEvidence`, `BrowserAudit`) | `backend/app/models/web_knowledge.py` |
| Migration + manifest entry (sequence 49, number 49) | `backend/app/db/migrations/049_browser_substrate.sql`, `backend/app/db/migrations/MIGRATION_ORDER.json` |
| Redaction, state machine, evidence files, attribution and standard envelope | `backend/app/services/browser_evidence_service.py` |
| Task creation records an attributed run; cancellation records real timestamps and audit; legacy `status: pending` preserved | `backend/app/services/autonomous_web_task_service.py` |
| UWAIE execution records per-step audit, screenshot/excerpt evidence, verification state and optional envelope via new `task_id` parameter | `backend/app/services/uwaie_service.py` |
| Unit tests | `backend/tests/test_browser_evidence.py` |

**Verified gates:**

- `python -m pytest backend/tests -q` → **662 passed**.
- `python -m ruff check` on all modified Python files → **all checks passed**.
- `python tools/api/check_migrations.py` → **OK** (49 files, 49 manifest entries, no duplicate prefixes).
- `python tools/api/print_openapi.py --check` → **DRIFT**, caused by `/api/v1/geo/render` from concurrent geo work. No route was added by WP-03; the snapshot was intentionally not regenerated here.

**Not yet done at that point:** live Postgres integration check, evidence retention sweeper, WP-04 queue and WP-05 API envelope routes.

### 9.3 Remaining gaps closed in this session

| Gap | Change |
|-----|--------|
| WP-03 integration check | `backend/tests/integration_db_check.py` now persists a browser run, evidence package and audit record against the throwaway Postgres database |
| WP-03 retention | `BrowserEvidenceService.purge_expired()` deletes expired evidence rows and files; bounded `increment_retry(max_retries)` added |
| WP-04 queue | `backend/app/workers/arq_browser_worker.py` now checks terminal state (idempotency via `job_id=task_id`), enforces deadlines, records bounded retries and never replays failed external actions; `backend/tests/test_browser_task_queue.py` added. Compose `browser-arq` profile already existed |
| WP-05 API | `/api/v1/browser` now exposes `POST/DELETE /sessions`, `POST /inspect`, `POST /execute`, `POST /verify`, `POST /tasks/{id}/cancel` in addition to task create/status/evidence; `/api/v1/browser` added to `ADMIN_PREFIXES`; public `UWAIEService.verify()` added; `backend/tests/test_browser_api.py` added |
| WP-06 smoke | `tests/browser_substrate_smoke.py` added — opt-in live public-site test printing `IAM_BROWSER_P1_OK`, `SKIPPED` otherwise |
| WP-07 docs | `IAM_CI_AND_WORKERS.md` documents the ARQ browser worker and smoke test; OpenAPI snapshot regenerated |

**Gates after these changes:**

- Focused browser tests: **26 passed**.
- Full backend suite: **698 passed, 2 failed** — both failures are in concurrent autonomy/governance work (`test_autonomy_graph_integration.py`, `test_ownerauth_reconciliation.py`), not in Doc 29 files. No changes were made to those subsystems.
- Ruff on all backend + smoke script: **all checks passed**.
- `python tools/api/print_openapi.py --check` → **OK**.
- `python tools/api/check_migrations.py` → the concurrent duplicate `020` prefix (`020_provider_registry_gates_reviewed.sql` and `020_security_work_sessions.sql`) was resolved by renaming the latter to `055_security_work_sessions.sql`; the migration manifest records the new path and unique prefix. Gate now reports OK.
- Smoke script without opt-in → `SKIPPED`, exit 0, no `IAM_BROWSER_P1_OK`.

**Later re-check (same day):** the duplicate `020` migration prefix and the two autonomy/governance test failures were resolved by concurrent work — `python tools/api/check_migrations.py` now reports **52 files / 52 manifest entries / 0 duplicate prefixes**, and both previously failing tests pass. They are no longer blockers.

**Remaining for P1:** (1) a live-stack run of the WP-06 smoke test — it needs a running stack plus an admin credential, and must print `IAM_BROWSER_P1_OK` with evidence IDs; (2) the signed OD-49 decision artefact from §1.1. P1 must not be marked complete until both are closed. Unit tests can prove the contract and persistence logic; only the live run proves a real browser performed the navigation and interaction.

---

## 10. Phase 2 — first implementation slice (Doc 29 §11 P2)

Owner direction: "start Phase 2". Scope of this slice: page understanding, structured extraction with provenance, independent verification, screenshot metadata and multi-tab coordination. Remaining P2 items (hosted-vision-independent OCR adapter, broader document parsing) stay open.

| Capability | File |
|------------|------|
| Semantic DOM script (roles, labels, forms, headings, landmarks, alerts, pagination, geometry; **no input values**) and extraction scripts (tables, listings, links, metadata) | `backend/app/services/browser_intelligence_service.py` |
| Local PNG dimension/hash metadata — no hosted vision model; page content marked untrusted | same file |
| `understand()`, `extract()`, `verify_extraction()` (independent re-extraction + digest comparison), `coordinate_tabs()` (unknown tab fails closed) | same file |
| Evidence and attribution wired through WP-03 `BrowserEvidenceService` | same file |
| `/api/v1/browser/intelligence/{understand,extract,verify,tabs/coordinate}` — admin-scoped via `/api/v1/browser` | `backend/app/api/routes/browser_intelligence.py`, `backend/app/main.py` |
| Tests | `backend/tests/test_browser_intelligence.py` |

**Gates:** 9 new tests pass; full backend suite **761 passed, 5 subtests passed**; ruff clean; OpenAPI drift check **OK**; migration check **OK** (54 files, no duplicate prefixes). OpenAPI snapshot regenerated.

**OCR gap closed (same day):** installed `pytesseract==0.3.13` (`backend/pyproject.toml`, `backend/requirements.lock.txt`) and added `tesseract-ocr`/`tesseract-ocr-eng` to the backend image (`backend/Dockerfile`). `TesseractOcrAdapter` runs locally off the captured screenshot via `asyncio.to_thread`, redacts text, and reports `{available: false, reason}` when the library or binary is missing — it never returns empty text that could look like a successful OCR pass. Gated by `BROWSER_OCR_ENABLED` (default `false`, exposed in `docker-compose.yml`). Two additional tests cover opt-in behaviour and fail-closed absence; 11 P2 tests pass.

**Document parsing gap closed (same day):** installed `pypdf==7.2.0`, `python-docx==1.2.0`, `openpyxl==3.1.5` (plus `lxml`, `et-xmlfile`) locally and recorded them in `backend/pyproject.toml` and `backend/requirements.lock.txt`. `backend/app/services/browser_document_service.py` fetches public http(s) URLs only (DNS/IP SSRF guard, redirect re-validation, size cap), parses PDF/DOCX/XLSX/HTML/text locally, attaches source provenance (URL, timestamp, sha256, bytes, content type), records evidence and audit, and never treats document text as instructions. `POST /api/v1/browser/intelligence/document` exposed it; 8 new tests cover SSRF denial, kind detection, all parsers, provenance and the route.

**Still open in P2:** a live-stack extraction/document smoke run. No P2 claim is made beyond the implemented slices; local OCR is claimed only when the adapter reports `available: true`.

**Concurrent unrelated gate state at final check:** full backend suite **803 passed, 2 failed** — failures are in concurrent model-selector and HBI translation-lab work, not in Doc 29 files; OpenAPI drift is from nine concurrently added `/api/v1/hbi/research/lab/*` and `/api/v1/hbi/knowledge/*` paths. Neither was modified or regenerated here. Migration check remains OK.

---

## 11. Phase 3 — Browser Security Gateway (owner: finish coding first)

Owner direction: finish code phases before the two external completion items. P3 is the first phase under that instruction.

| Capability | File |
|------------|------|
| Permission checks delegated to existing `InternetAccessService`; prompt-injection detection delegated to existing `AegisEngine`; conservative phishing/impersonation URL heuristics | `backend/app/services/browser_security_gateway.py` |
| Download quarantine: hash, size, extension risk, isolated quarantine directory, `executed: false`, signed-approval release via `CreatorApprovalService` | same file |
| Auditing through WP-03 `BrowserEvidenceService`; website text treated as untrusted data and instructions explicitly ignored | same file |
| `/api/v1/browser/security/{inspect, permission/{action_type}, download/quarantine, download/release}` | `backend/app/api/routes/browser_security.py`, `backend/app/main.py` |
| Adversarial tests | `backend/tests/test_browser_security.py` |

**Gates:** 8 new tests pass; ruff clean. Full-suite and OpenAPI gates still reflect concurrent HBI/model work noted in §10 and were not regenerated here.

**Next code phases:** P4 (Web Knowledge Integration + source verification), P5/TIPS foundation, P6/TIPS onion + privacy, P7 (multi-agent scale), P8 (hardening/lifecycle). No claim is made for those phases yet.
