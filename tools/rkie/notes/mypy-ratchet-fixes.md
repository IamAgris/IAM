# Mypy ratchet drift fixes

**Date:** 2026-11-27 · **Based on:** working tree at commit `34d5177` plus uncommitted work
**Re-verify:** `python tools/quality/check_mypy_ratchet.py`; mypy cache can go stale after
concurrent edits — confirm with `--no-incremental` before editing.

## Problem

The ratchet reported 26 new strict-typing errors, rising from late-arriving browser,
geospatial, IPLCI and orchestration modules. Fixing those exposed further errors as
other files appeared; the final stable result was **0 new errors, 97 fixed**.

## Pattern used

- SQLAlchemy `Column[...]` attributes were being assigned Python values or passed to
  typed helpers. Cast the loaded row to `Any` at the point of mutation/
  envelope-building rather than changing the ORM declarations.
- Untyped new helpers (`_ensure_browser`, route handlers, workers) got explicit
  annotations (`-> None`, `-> Response`, `-> Dict[str, Any]`, `ctx: Dict[str, Any]`).
- Optional mappings were narrowed before `.get()`; `bool(...)` wrapped comparisons
  returning `Any`; renamed a redefined `result` local.
- New ORM classes added `# type: ignore[misc]` for the existing `Base`-is-`Any` pattern
  already present in `web_knowledge.py`.

## Files touched

`browser_evidence_service.py`, `web_knowledge.py`, `autonomous_web_task_service.py`,
`browser_service.py`, `geo_service.py`, `api/routes/geo.py`, `uwaie_service.py`,
`request_context.py`, `arq_browser_worker.py`, `api/routes/browser.py`,
`iplci/continuity.py`, `iplci/service.py`, `autonomy_graph.py`, `model_policy.py`,
`api/routes/research.py`.

## Gate status after fixes

OpenAPI drift OK, migrations OK, ruff OK, strict mypy (`mypy.ini`) OK,
ratchet OK, coverage **705 passed / 66.69%**, RKIE index refreshed.
