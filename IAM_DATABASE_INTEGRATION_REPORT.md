# Database Integration Report

**Run date:** 25 November 2026  
**Target:** throwaway database `aura_integration_test` on the running `aura-postgres` container. The live `aura_db` was not touched.

Reproduce from `backend/`:

```powershell
$env:POSTGRES_PASSWORD = (Get-Content ..\.env | Where-Object { $_ -like 'POSTGRES_PASSWORD=*' }).Split('=',2)[1]
$env:POSTGRES_PORT = '5434'
$env:DATABASE_URL = "postgresql+asyncpg://aura:$env:POSTGRES_PASSWORD@127.0.0.1:5434/aura_integration_test"
python tests/integration_db_check.py
```

## Result: PASS

`alembic upgrade head` now succeeds from an empty database: `0001_initial` was
regenerated from ORM metadata in foreign-key dependency order. Migrations
`002_skillforge.sql`, `003_security_engines.sql`, `004_creator_email_approval.sql`,
`005_retire_legacy_owner_authorizations.sql`, `006_creator_email_outbox.sql`,
`007_api_credentials.sql`, `008_retire_legacy_approval_requests.sql` and
`009_skill_runtime.sql` then apply cleanly (idempotently). 141 relations present,
including `alembic_version`. `alembic downgrade base` also
succeeds; the archived `legacy_owner_authorizations` table is deliberately retained.
All lifecycle checks passed against real PostgreSQL:

- Skill Forge personal skill: create → validate → test → publish → activate → new version → rollback
- Skill Runtime: gated invocation → simulated result; ungranted permission → denied + audited
- Skill Forge sensitive skill: create → validate → test → email request → outbox delivery → signer challenge → signed decision → publish
- ARTEX engine: signed registration → signed scope → signed security-testing authorization → task → signed task approval → dry-run dispatch → sync
- Findings: normalisation → remediation → Skill Forge defensive-skill handoff
- Governance: authority boundary → signed Creator authorization → permitted
- HTTP auth: unauthenticated admin path → 401, admin key → 200, user key → 403, public health → 200
- External-presence integration: connect → email request → activation blocked → signed approval → activation allowed

## Bugs found and fixed during the check

1. **`001_initial_schema.sql` / `0001_initial.py`:** `financial_ledger` referenced
   `financial_transactions` before that table was created. Reordered in both files.
2. **`security_engine_tasks` audit insert:** `task.id` was read before `flush()`,
   sending the string `"None"` to a UUID column. Added `await db.flush()` in
   `SecurityEngineService.create_task()`.
3. **Governance and internet-access services** still consulted the removed
   `OwnerAuthService`. Both now use `CreatorApprovalService.check_authorization()`.

## Migration fix applied

- `app/db/migrations/versions/0001_initial.py` previously had **27 forward
  foreign-key references** and `app/db/migrations/001_initial_schema.sql` created
  only **45 of 135** tables. Both were hand-written and had drifted from the models.
- Both files are now generated from `Base.metadata.sorted_tables` by
  `app/db/migrations/generate_initial_schema.py`, which emits DDL in dependency
  order. The only remaining "forward reference" is the intentional self-reference
  on `security_engine_tasks.parent_task_id`.
- `env.py` now imports all models, so Alembic sees the complete metadata.
- After changing models, regenerate with:
  `cd backend && python -m app.db.migrations.generate_initial_schema`
  Then review the diff — this rewrites the base migration.

## Non-blocking warnings

- `alembic downgrade base` may leave `legacy_owner_authorizations` in place on
  databases that predate the cleanup. Fresh databases no longer create it. It is
  inert and unreferenced by code.
- SQLAlchemy emits two pre-existing `SAWarning`s about overlapping relationships
  in `app/models/worldmodel.py` (`EntityRelationship.source_entity` /
  `target_entity` vs `WorldEntity.relationships_as_source` / `_as_target`).

Add `overlaps=` or `viewonly=True` in `worldmodel.py` when that model is next touched.
