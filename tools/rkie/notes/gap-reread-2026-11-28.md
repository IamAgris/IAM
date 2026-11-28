# Open-gap re-read against the working tree — 28 November 2026 (final pass)

**Basis:** working tree with substantial concurrent owner work. This is a local
evidence record, not an amendment to any authoritative document.

## Resolved in this pass

| Item | Evidence |
|---|---|
| O-4 CI `types` discrepancy | Public GitHub Actions API at owner head `ab8aaa8`: Supply chain, IAM CI, RKIE, CodeQL and **Quality gates** all `conclusion: success`. Local `check_mypy_ratchet.py`: 0 errors, baseline 0, RESULT OK. (`gh` CLI is unavailable; the public API sufficed.) |
| O-6 source-first live validation | `IAM_LIVE_E2E=1 python tests/e2e_live_information_smoke.py` exited 0: provider `duckduckgo-http`, escalation fired, Wikipedia excluded, 3 live results including `sabcnews.com`. No patched provider responses. |
| O-7 `schedule_at` defect | `create()` persists validated timezone-aware schedule; API exposes it; 2 tests; OpenAPI snapshot includes the field. See `schedule-at-g17-fix-2026-11-28.md`. |
| O-9 module contract registry | `services/module_registry.py` (10 contracts) wired into `dispatch.py` / `autonomy_graph.py`; `GET /api/v1/capabilities/modules`; `test_module_registry.py` 4/4. |
| O-10 memory sweeper + UI voice | `expire_memories`, `find_duplicate_memories`, `consolidate_memories` wired into `arq_model_catalog.py` cron with `test_memory_lifecycle.py`; `interface.tsx` calls both voice routes with browser fallbacks and now sends UI locale. |
| O-12 skills + CLI | CLI `login`/`dev init` implemented; `iam/skills/native/` holds `secret-redaction` and `evidence-summary`. |
| O-13 HBI claim mismatch | `hbi/modules.py` docstring corrected to match `IMPLEMENTED` (all 38); `test_hbi.py` 91/91. |
| Web3 preflight test failures | `test_deployment_preflight.py` + `test_web3_adapters.py` now pass (29/29) after owner changes. |

## Genuinely blocked — no evidence can be manufactured here

| Item | Why |
|---|---|
| O-8 two physical nodes | One host only. `known_hosts` contains `169.58.234.90`, but SSH auth fails for `root`/`ubuntu`/`azureuser` (Permission denied; no key or `~/.ssh/config`). A two-container/two-process run would not satisfy a physical-node requirement. |
| O-11 git tags | `GET /api.github.com/repos/IamAgris/IAM/tags` returns `[]`; local `git tag -l` is empty. `git push --dry-run` succeeds (credential manager configured), so auth is not the blocker — the blockers are the absence of an agreed tag name/commit and a clean tree (598 uncommitted entries at `f068af8`). (`.sops.yaml` exists, `check_infra_drift.py --json` OK, `/metrics` exists.) |
| O-14 real GPU fine-tune run | `ai_research/training.py` states "No substantial training is run on the 8 GB core"; the only local GPU is a 6 GB GTX 1660 Ti and `local_ollama_training.py` is explicitly prompt/template adaptation, not weight fine-tuning. A real run belongs on the governed external/Colab path with dataset provenance. |

## Gate state at end of pass

`pip-audit` clean; `npm audit` 0 in all three workspaces; ruff clean; migrations
70/70; OpenAPI 861/861 and 488/488 after regeneration (includes `schedule_at`);
mypy ratchet OK; frontend production build passes; mypy + 2 previously failing
Web3 tests green. All changes remain uncommitted.
