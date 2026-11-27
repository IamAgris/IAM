# Technology Capability Registry (Doc 20 / OD-36) — implementation map

**Date:** 27 November 2026 · **Based on:** current working tree (uncommitted), verified by
`Search-IAMRepo.ps1 -Query "Technology Capability" -Mode content -Scope backend` (no results
before implementation) and `-Mode files` for `registry` (only `ai_research/registry.py` and
`financial_intelligence/provider_registry.py` existed).

This registry is **distinct** from:
- `backend/app/models/capability.py` — IAM's own capability/assessment registry;
- `backend/app/services/ai_research/registry.py` — MEFE model registry;
- `backend/app/services/financial_intelligence/provider_registry.py` — finance providers.

## Files

| File | Role |
|------|------|
| `backend/app/models/technology.py` | `TechnologyCapability` table (licence, cost, architecture, lifecycle, benchmarks) |
| `backend/app/services/technology_registry_service.py` | Register/list/get/state/benchmark; lifecycle gate forbids direct researched→integrated |
| `backend/app/api/routes/technology_registry.py` | `/api/v1/technology-registry/*` |
| `backend/app/db/migrations/040_technology_capabilities.sql` | DB table + indexes |
| `backend/tests/test_technology_registry.py` | 7 unit tests (no DB) |
| `IAM_API_CONTRACTS.md` | Endpoint contracts |

## Verification

- 7/7 new unit tests pass; app imports with 88 routes.
- Migration applied to live Postgres; backend rebuilt healthy.
- OpenAPI exposes all five registry paths.
- Live smoke: register → 201 `researched`; illegal transition → 400; legal transition → 200 `tested`; list → 200.

## Boundaries

The registry records research only. It does not install, execute or approve code.
`integrated` requires the ordered path and OD-11 creator approval before any protected-core change.
