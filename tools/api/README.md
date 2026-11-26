# API contract tooling

Deterministic, local-first tooling for the IAM OpenAPI contract. It uses the
live FastAPI app as the source of truth and never calls an external service.

## Regeneration and drift check

```powershell
python tools/api/print_openapi.py --check              # CI gate; exit 1 on drift
python tools/api/print_openapi.py --update             # deliberately refresh snapshot
python tools/api/print_openapi.py --output spec.json   # write a copy elsewhere
```

`IAM_OPENAPI.json` at the repository root is the snapshot. `--check` compares
path sets and schema counts and prints declared-but-missing and
snapshot-but-removed paths. It is wired into `.github/workflows/openapi-drift.yml`.

**Current state (27 November 2026 working tree): DRIFT.** The live app exposes
**536 paths / 332 schemas**; the snapshot has **505 / 320**. 31 declared paths
are absent from the snapshot, mostly HBI and interface routes from uncommitted
work. Refresh the snapshot with `--update` only after reviewing that change as
an approved contract update. The older note in `IAM_EXTERNAL_MODULES_REVIEW.md`
claiming 442 live paths is itself stale.

`backend/print_spec.py` (uncommitted user file) also regenerates the snapshot
but uses a hardcoded absolute Windows path. The portable tool above replaces it
for gate use; the old file was deliberately left untouched.

## Supply-chain configuration

Added as new files only — `.github/workflows/ci.yml` was not modified:

- `.github/dependabot.yml` — weekly updates for backend/pip, SDK Python/pip,
  frontend/npm, both TS SDKs/npm, Docker and GitHub Actions.
- `.github/workflows/supply-chain.yml` — `pip-audit` on installed backend
  dependencies, `npm audit --audit-level=high` per npm workspace, gitleaks
  secret scan, and an SPDX SBOM uploaded as an artifact.

Known limitations: the backend has no Python lockfile, so `pip-audit --local`
audits whatever `pip install -e ./backend` resolves; gitleaks may require a
licence for organisation-owned repositories; none of the workflow jobs were
executed during the local audit (only YAML syntax was validated).
