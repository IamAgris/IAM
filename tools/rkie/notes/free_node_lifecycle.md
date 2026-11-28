# Free infrastructure node lifecycle (Doc 19 / OD-35)

**Date:** 27 November 2026 · **Based on:** current working tree; verified with
`Search-IAMRepo.ps1 -Query lifecycle -Mode files -Scope backend` (only `ai_research/lifecycle.py`
and `hbi/lifecycle.py` existed) and Doc 19 spec in `docs/ARCHITECTURE_INDEX.md`.

This is **not** Doc 22's `free_sandboxes` (notebooks/spaces). It assesses cloud VM nodes
(GCP/AWS/Railway-class) for supplementary use and manages their lifecycle.

## Files

| File | Role |
|------|------|
| `backend/app/models/freenode.py` | `FreeNodeCandidate` — provider, arch, resources, verification, usefulness, status, expiry |
| `backend/app/services/free_node_lifecycle.py` | Usefulness gate + record/verify/set-status/migration-plan; no provisioning |
| `backend/app/api/routes/freenodes.py` | `/api/v1/free-nodes/*` |
| `backend/app/db/migrations/042_free_node_candidates.sql` | Table + indexes |
| `backend/tests/test_free_node_lifecycle.py` | 9 unit tests (no DB) |

## Verified

- 9/9 unit tests; app imports with 90 routes.
- Migration applied; backend rebuilt healthy.
- Live flow: record → `201 assessed`; deploy without verified terms → `400`;
  verify-terms → `200`; deploy → `200`; migration-plan → `200 expiring`; list → `200`.

## Boundaries

Free availability alone never justifies a node: CPU/RAM, run compatibility, acceptable
overhead and security exposure, and demonstrated net benefit must all pass. No account
creation, VM provisioning, spending or limit bypass is implemented. Deployment still needs
creator authorisation (OD-03/25) and any registered node remains a candidate until attested
(OD-12/13).
