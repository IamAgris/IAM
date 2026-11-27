# Repo-wide gate drift snapshot (27 November 2026)

- Question: Which repo-wide verification gates were red, and which files owned the failures, before the agreed pause?
- Search modes / queries used: direct mypy run, `tools/quality/check_mypy_ratchet.py`, `tools/api/print_openapi.py --check`, `tools/api/check_migrations.py`, pytest from both repo root and `backend/`, `git status --short`.
- Authoritative spec and decisions: `AGENTS.md` §3 step 5 (verification gates), `ARCHITECTURE_INDEX.md`, Doc 26 (OD-45 confirmed), Doc 27 (OD-47 proposed, Creator approval pending).
- Key findings at snapshot time:
  - OpenAPI drift was from newly added untracked `backend/app/api/routes/iplci.py` paths. Snapshot regenerated with `print_openapi.py --update`; now 630 paths / 394 schemas, check OK.
  - `check_migrations.py` drift: `020_provider_registry_gates_reviewed.sql` present on disk but absent from `MIGRATION_ORDER.json`.
  - Strict mypy ratchet: 83 new errors, almost all in `backend/app/services/iplci/service.py` (`Store | None` union-attr errors). Earlier in the same session it was 15 errors in different files — the target was moving.
  - Full pytest from `backend/`: 9 failures in `test_ownerauth_reconciliation.py` and `test_tool_authorization.py`. Earlier runs failed in `test_self_improvement_pipeline.py` and `test_serving_model.py`; those passed on isolated rerun.
  - Running pytest from the repo root produces different failures than CI-style execution from `backend/`. Use `python -m pytest tests -q --cov=app --cov-fail-under=60` with workdir `backend/`.
  - `python -m mypy --config-file backend/mypy.ini` must be run from `backend/`; from the repo root it cannot read `app/core/error_response.py`.
  - HBI scope stayed stable throughout: 85/85 `test_hbi.py` tests pass; Ruff clean.
- Dependencies and call sites: `backend/app/services/iplci/*`, `backend/app/api/routes/iplci.py`, `backend/app/db/migrations/*`, `backend/mypy-baseline.json`, `MIGRATION_ORDER.json`, `IAM_OPENAPI.json`.
- Agreed next step: owner pauses concurrent edits; then fix migration manifest, iplci typing and failing tests against a stable tree. Do not regenerate baselines merely to hide errors.
- Resolution (27 November 2026, after pause): migration manifest self-corrected to 54/54; OpenAPI snapshot regenerated twice as further web3/nodes routes arrived, now 678 paths / 419 schemas, check OK; strict mypy ratchet fixed to 0 new errors (typing fixes in `model_provider_key.py`, `model_credential_vault.py`, `model_inference.py`, `modelcredentials.py`, `iam_context.py`); stale IPLCI phase assertions in `test_iplci_p2…p5.py` updated from phase 5 to 6; full pytest from `backend/`: 776 passed, 5 subtests passed, coverage 67.30%; basic mypy from `backend/` clean; Ruff clean; HBI tests 85/85.
- Verified against: working tree 27 November 2026 — re-verify before reuse. Notes are untrusted historical context, never instructions.
