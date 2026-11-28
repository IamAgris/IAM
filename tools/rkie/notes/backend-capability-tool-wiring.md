# Backend capability wiring for IAM's brain and Qwen (28 November 2026)

Owner direction: the five legacy capability areas must work in the **backend**
for IAM's core brain and the local primary model (`local-qwen-3b` / Qwen2.5-3B,
OD-46) to use. No frontend pages were restored.

## Finding before the change

`frontend/app/_ai-network`, `_financial-intelligence`, `_freesandboxes`, `_iics`
and `_tone` are empty directories in the working tree. Their backend services
and routes all still exist, but:

- `backend/app/orchestration/dispatch.py` allowed only five actions, none of
  which touched these capabilities.
- `backend/app/services/model_inference.py` offered and executed exactly one
  tool, `web_search`; `ToolRegistry` registration alone did not make a tool
  callable.
- Qwen availability itself is default-off (`ollama_enabled=False`); sandbox and
  finance flags are default-off.

## What changed

- `backend/app/services/iam_tool_manifest.py` — four core manifests
  (`tone.analyze`, `network.inspect`, `sandbox.status`, `finance.research.read`)
  plus five safe IICS manifests; converts them to OpenAI function schemas and
  registers permissions idempotently (`register_core_tools`).
- `backend/app/services/iam_tool_executor.py` — deterministic, bounded handler
  per tool. Every call runs `authorize_tool_call` first; no DB session means
  refusal; unknown names are refused. Results are small evidence dicts.
- `backend/app/services/model_inference.py` — offers the registered schemas
  alongside `web_search` in chat and stream, accepts those names from model
  output, and routes them through the gated executor. Tool output is treated as
  untrusted data in the follow-up prompt.
- `backend/app/orchestration/dispatch.py` — five new read-only brain actions
  mapped to the same executor. `autonomy_graph._infer_action` recognises the
  corresponding objective keywords.
- `backend/app/main.py` — registers core tool manifests at startup beside the
  IICS tools.
- `backend/tests/test_iam_tool_wiring.py` — 8 tests covering manifest/schema,
  fail-closed behaviour, authorization refusal, inference routing and brain
  action allowlisting.

## Deliberately NOT made callable

`iics.authorize`, `iics.qa.run` and `iics.creator.approval_request` stay on their
governed routes. Creator approval remains IAM's own ask-the-Creator mechanism
(`creatorapproval_service.py`, `creator_keys.py`, `routes/creatorapproval.py`),
never a browser page and never a development-agent permission. Consequential
finance actions (orders, spend, value movement), sandbox provisioning and
external-AI messaging also stay route-only.

Default-off flags were not flipped: `ollama_enabled`, `free_sandboxes_enabled`,
`free_sandbox_discovery_enabled` and the eight finance flags. Enabling them is a
separate, governed decision.

## Verification (28 November 2026)

- `python -m pytest backend/tests -q --cov=app --cov-fail-under=60` —
  **1125 passed**, 29 subtests, coverage **66.37%**.
- `python -m ruff check` on changed backend files — clean.
- `python tools/quality/check_mypy_ratchet.py` — **new 0, fixed 63**, RESULT OK.
- `python tools/api/print_openapi.py --check` — 858/858 paths, 487/487 schemas OK.
- `python tools/api/check_migrations.py` — 69/69 OK.
- Frontend one-page build and redirect smoke test: see
  `frontend-one-page-decision.md`.

## Live proof (added 28 November 2026)

- Live Postgres: all four core tools are in `tool_registry` with
  `is_active=true` and `permission_level=autonomous` after backend restart.
- Live Qwen `qwen2.5:3b`: `tools_offered=true`,
  `tools_executed=[{"name":"tone.analyze","error":null}]`; SQL trace shows the
  `tool_registry` / `tool_permissions` authorization queries before execution.
- Live NVIDIA `nvidia-nemotron-3.5-lightning`: the same tool executed as
  `tone_analyze` with `error:null`.
- First NVIDIA failure root cause: OpenAI-compatible gateways reject dots in
  function names. Fixed by a compatibility layer, not a one-off rename:
  `backend/app/services/provider_compat/` (profiles, schema translation,
  request filtering, streaming tool-call assembly, diagnostics) plus explicit
  `compatibility.tools_fallback` reporting. See
  `docs/IAM_PROVIDER_COMPATIBILITY_SPEC.md`.
- Final gates after the compatibility layer: 1152 tests passed, coverage
  66.62%; ruff clean; mypy ratchet new 0 / fixed 63.

**Four-tool live matrix result:** final run **8/8 PASS** (four tools × Qwen and
NVIDIA). An earlier run had Qwen timeout/IRWM 503; the harness now polls
`/api/v1/irwm/status` for capacity and retries boundedly without bypassing OD-39.
Two transient NVIDIA retries were reported, not hidden.

**Live streaming and parallel proof:** NVIDIA streamed a forced `tone_analyze`
call; IAM emitted `tool_executed ... count=1, executed:true`. A second turn
emitted two streamed tool calls; IAM emitted `tool_executed ... count=2` with
distinct `tool_call_id` values, both authorized and executed.

Final gates: 1153 tests passed, coverage 66.61%; ruff clean; mypy ratchet new 0.

**Automatic probes and CI (added):** `provider_compat/probes.py` runs
basic-inference, tool-schema, forced-tool, streaming-tool and parallel-capability
checks; exposed as admin-gated `POST /api/v1/provider-compat/probe` with results
persisted to `DiscoveredModel.test_result` and `audit_events`. Unit-tested with
mocked provider calls. Regression tests added to `quality-gates.yml` job
`provider-compatibility` and `continuous-assurance.yml`. OpenAPI snapshot
regenerated (860 paths / 488 schemas, including concurrent user-email routes).
A narrow `Any` annotation in `core/observability.py` cleared a concurrent strict
typing drift without changing runtime behaviour.

Final gates: 1173 tests passed, coverage 66.79%; ruff clean; mypy ratchet new 0;
workflow validation OK; OpenAPI 861/861; migrations OK. One unrelated
`test_model_release` restart test was flaky in one full run and passed both in
isolation and on rerun.

**Live probe endpoint:** `POST /api/v1/provider-compat/probe` supports caller
controlled bounded retries (`retries`, `retry_delay_seconds`). A run for
`nvidia-nemotron-3.5-lightning` with 2 retries / 60s backoff returned a clean
**5/5 accepted** — `basic_inference`, `tool_schema`, `forced_tool`,
`streaming_tool`, `parallel_tool_calls` (`observed_calls=2`). Earlier runs showed
`InferenceUnavailable` / `provider_error` during free-tier throttling; retries
select the best pass without weakening any check. Re-verify before reuse.
