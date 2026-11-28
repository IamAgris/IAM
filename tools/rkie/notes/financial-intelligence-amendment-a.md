# Financial Intelligence — Doc 25 Amendment A

**Date:** 2026-11-27 · **Based on:** commit `ab87b8f` plus uncommitted working-tree work
**Re-verify before reuse:** file hashes change; run `tools/rkie/Check-IndexFreshness.ps1`.

## What landed

Doc 25 `docs/IAM_FINANCIAL_INTELLIGENCE_AND_ECONOMIC_INDEPENDENCE_SPEC.md` was expanded
(v1.2, §§11–24): prediction markets, gaming/casino intelligence, investments, provider
ecosystem, South African boundaries, autonomy matrix and implementation status.
Sections 1–10 and OD-04/OD-25 financial authority were unchanged. Amendment A was
recorded as **OD-56** (OD-53/OD-55 are reserved Web3 proposals; OD-54 is live information).

Code (research-only; no wagering, wallet funding or real orders):

- `backend/app/models/financial_intelligence.py` — markets, estimates, forecasts, gaming,
  investment and provider-registry tables.
- `backend/app/services/prediction_markets/{service,adapter,forecasting}.py` — research,
  read-only Gamma/CLOB/Data API adapter, independent probability forecasting.
- `backend/app/services/financial_intelligence/{policy,provider_catalogue,provider_registry}.py`
  — 37 §18 candidates, all gates unreviewed, all adapters disabled.
- `backend/app/services/gaming_intelligence/service.py`,
  `backend/app/services/investment_intelligence/service.py` — study only; wager/order
  methods always deny.
- `backend/app/api/routes/financial_intelligence.py` — 27 research endpoints under
  `/api/v1/prediction-markets`, `/gaming-intelligence`, `/investment-intelligence`,
  `/provider-registry` (27 paths).
- `frontend/app/financial-intelligence/page.tsx` and sidebar entry.
- Migrations: `030_financial_intelligence.sql`, `versions/0002_financial_intelligence.py`.
- Generated `IAM_OPENAPI.json`: 829 paths / 473 schemas after the 2026-11-27
  drift fixes (the financial-intelligence routes themselves were added at 505/320).

## Verification (2026-11-27)

- `python -m compileall -q backend/app` — pass.
- `python -m unittest discover -s tests -p 'test_*.py' -q` — 385 tests, OK on 2026-11-27
  rerun (the count includes unrelated uncommitted test files that appeared during verification).
- `python tests/hbi_acceptance_check.py` — 10 gates passed.
- `npm run build` (frontend) — pass, `/financial-intelligence` static route.
- `tools/rkie/Update-Index.ps1`, `tools/rkie/tests/Test-RKIE.ps1` — 20 passed, 0 failed.
- `pytest backend/tests -q --cov=app --cov-fail-under=60` — **626 passed, 65.84%**
  coverage (gate passed). Locally this needs
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` plus `-p pytest_cov`: the environment blocks a
  `langsmith` plugin dependency (`xxhash` DLL). `pytest-cov` itself is installed.

## Boundaries

Every feature flag is default-off. New API prefixes require `admin` scope. Legal
clearance records review only; `real_money_enabled`, `wagering_enabled`,
`execution_enabled` and the execution adapter stay false. South African participation
needs specialist legal advice; none is granted by this work.
