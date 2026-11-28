# Infisical Cloud secrets source (OD-58 / Doc 38)

**Based on:** working tree 28 November 2026. Re-verify against current files before reuse.

## Finding

Owner confirmed **Option C — Infisical Cloud, dual-read** on 28 November 2026.
OD-07 (SOPS + Docker secrets) is **not replaced**: it stays the baseline and the
fallback. The OD-51 §4.1 provider-key vault is a separate local system and was
not touched. No Infisical code, dependency or config existed before this change.

## Files added / changed

- `docs/IAM_INFISICAL_SECRETS_DECISION.md` — Doc 38 / OD-58 decision request and record.
- `docs/IAM_OWNER_DECISIONS.md` — OD-58 confirmed section; count 53 → 54; change-control note.
- `docs/ARCHITECTURE_INDEX.md` — authoritative count, Doc 38 row, derived-doc parents.
- `docs/IAM_PRIVACY_AND_SECRETS.md`, `docs/IAM_DEPLOYMENT_CONFIG.md` — operational notes.
- `backend/app/core/infisical.py` — REST client (Universal Auth login, `/api/v4/secrets`),
  TTL cache with last-known-good, HTTPS host allowlist, redacted status. Uses the
  already pinned `httpx`; no new dependency.
- `backend/app/core/config.py` — `secrets_backend` (default `docker`) and `infisical_*`
  settings; `thirdweb_client_id` added to `SECRET_FIELDS`.
- `backend/app/core/secrets.py` — `read_secret()` consults Infisical first only when
  the flag is set, then Docker `<FIELD>_FILE` / environment. `enforce_secret_policy()`
  unchanged, so production still fails closed on missing/placeholder values.
- `backend/app/services/deployment_preflight.py` — `secrets_backend` and `infisical_*`
  checks; names/status only, never values.
- `backend/tests/test_infisical_secrets.py` — 11 tests including precedence, fallback,
  TTL login reuse, host rejection and redaction.

## Verification

`python -m pytest tests -q --cov=app --cov-fail-under=60`: 1092 passed, 66.48% coverage.
`ruff` clean on changed files. Strict mypy ratchet: 0 new errors.

## Reuse warning

Nothing is connected until `SECRETS_BACKEND=infisical`, a project ID and machine-identity
credentials are supplied. Production secrets must stay in the `dev`/`staging`/`prod`
environments of one Infisical project; never grant dev read access to prod.
