# Quality tooling

Deterministic, local-first quality gates. No network or LLM required.

## Strict typing ratchet

```powershell
python tools/quality/check_mypy_ratchet.py
python tools/quality/check_mypy_ratchet.py --update-baseline
```

`backend/mypy-full.ini` runs mypy with `strict = True` over the entire
`backend/app` tree. The repository has substantial pre-existing typing debt
(2,035 normalized errors at the time of writing), so `backend/mypy-baseline.json`
records the current debt and the gate fails only on **new** errors or new
occurrences of known errors. Fixing errors always passes; regenerate the
baseline deliberately after an intentional reduction.

New, self-contained modules are held to strict typing with no baseline at all
via `backend/mypy.ini` (`error_response.py`, `tool_authorization.py`, `ops.py`).
Extend that file list as modules are cleaned up.

Both checks run in `.github/workflows/quality-gates.yml` (`types` job).

## Other gates

| Gate | Command |
|------|---------|
| Lint (blocking rules) | `python -m ruff check backend` |
| Unit tests + coverage floor | `python -m pytest backend/tests -q --cov=app --cov-fail-under=60` |
| SDK contracts | `npm test` in `sdk/typescript`, `pytest` in `sdk/python` |
| OpenAPI drift | `python tools/api/print_openapi.py --check` |
| Migration order | `python tools/api/check_migrations.py` |
| Repository search | `tools/rkie/tests/Test-RKIE.ps1` |

Additional quality tooling:

```powershell
python tools/quality/mypy_debt.py --top 10 --json
python tools/quality/check_workflows.py --json
```

`mypy_debt.py` reads the ratchet baseline, ranks the worst files and error
codes, and records a history in `index/mypy-debt.json` (optionally with
`--target N`). Baselines are versioned by interpreter
(`backend/mypy-baseline-3.12.json` for CI, `...-3.15.json` for this host) because
mypy reports a different error set per Python version; the tools select the
matching file automatically. Manual annotation of small files has already reduced the
baseline from 2,054 to 1,954 errors. `annotate_signatures.py` is a libcst
codemod for mechanical `Any` annotations; it is unavailable on hosts where
Windows App Control blocks libcst's native extension, but it was executed
successfully inside `python:3.12-slim` on 10 non-route backend files (73
annotations, backend suite 910 passed, coverage 67.68%). Concurrent feature
work added more errors than that pass removed, so the baseline still stands at
~2,000 — the ratchet prevents further regressions.

`check_workflows.py` parses every `.github/workflows/*.yml`, checks that
referenced local scripts exist, and rejects hardcoded `ref: testing`; it
cannot replace an actual Actions run. `run_local_ci.py` runs the deterministic
gates in CI order locally (`--only <name>` to select steps), excluding the
compose-based acceptance job.

Runner setup is documented in `SELF_HOSTED_RUNNER.md`: GitHub-hosted runners
are already active on push/PR; a labelled self-hosted runner and an `act`
local runner are both supported. `.github/workflows/self-hosted.yml` is a
manual-only job targeting `[self-hosted, iam, windows]`.

All are wired into `.github/workflows/` as additive workflow files; the
user-modified `ci.yml` is untouched.
