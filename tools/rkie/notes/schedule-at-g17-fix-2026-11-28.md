# G17 — `schedule_at` fix — 28 November 2026

**Basis:** working tree at `a0972c7` with substantial concurrent owner work. Re-verify before reusing.

## Change

`docs/IAM_ARCHITECTURE_COMPLETION_AUDIT.md` G17 records that
`autonomous_web_task_service.create()` ignored `schedule_at`. Fixed:

- `backend/app/services/autonomous_web_task_service.py` — parse ISO 8601
  `schedule_at` (accepts `Z`, requires a timezone; rejects invalid/naive values
  with `AutonomousWebTaskError`) and persist it instead of hardcoding `None`.
- `backend/app/api/routes/autonomous_web_task.py` — expose `schedule_at` on
  `TaskCreate` and pass it through (invalid values → HTTP 400).
- `backend/tests/test_web_knowledge.py` — 2 new tests (persistence, rejection).
- `IAM_OPENAPI.json` — regenerated with `python tools/api/print_openapi.py
  --update`; 861/861 paths, 488/488 schemas, `--check` OK. The regeneration also
  absorbed a concurrently added `/api/v1/iplci/validation/seed-free-evidence`
  route that had already drifted in the working tree.

## Verification

`pytest backend/tests/test_web_knowledge.py` 17/17; full suite 1171 passed,
2 failed (see below); coverage 66.78%; ruff clean; migrations 70/70; OpenAPI OK.

## What this does NOT close

G17 also says "no worker executes decomposition or scheduled activity". Nothing
in the tree consumes `AutonomousWebTask.schedule_at`. Executing scheduled web
actions needs a session token, verification payload and an explicit permission
scope (UWAIEService.execute / OD-27/OD-49 permission matrix); adding that would
be a silent Research → Operate authority expansion. It needs an owner decision,
so it was deliberately not implemented.

## Concurrent-work regressions observed (not caused by this fix)

- `backend/app/orchestration/reasoning_engine.py` — 2 new mypy
  `no-redef` errors (`_typed_result` defined twice); ratchet DRIFT.
- `test_deployment_preflight.py::...ready_and_redacted` and
  `test_web3_adapters.py::ActivationTests::test_all_flags_off_is_ready` fail
  because new Web3 OD-55 preflight blockers/flags were added concurrently.
  Both files are modified in the working tree; left untouched.
