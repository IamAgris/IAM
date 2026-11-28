# IAM — Infisical Secrets Source Decision Request

**Document:** 38 (companion to OD-07 / `IAM_PRIVACY_AND_SECRETS.md`; next free number after proposed Doc 37)  
**Version:** 1.1 · 28 November 2026 (owner selection recorded)  
**Status:** **CONFIRMED — Option C (Infisical Cloud, dual-read), 28 November 2026. Default-off; OD-07 remains the baseline and Docker secrets remain the fallback.**  
**Parent:** `ARCHITECTURE_INDEX.md`, `IAM_OWNER_DECISIONS.md`  
**Related:** `IAM_PRIVACY_AND_SECRETS.md`, OD-07 (secrets), OD-10 (dev/prod credential separation), OD-11 (protected core), OD-15 (replaceable, free/open-source/self-hosted tooling), OD-51 §4.1 (provider-key vault)  
**Decision:** **OD-58 — CONFIRMED (28 November 2026): optional Infisical Cloud secrets source (Option C), dual-read with Docker secrets as fallback.** OD-07 remains the baseline; OD-57 is reserved for the paid-model proposal.

---

## 1. Current position

- **OD-07 is LOCKED:** "SOPS-encrypted env files + Docker secrets initially; migrate to Vault if scale requires." `IAM_PRIVACY_AND_SECRETS.md` records this as the operational policy. The decision register is frozen: any change requires the owner to explicitly reopen the decision with a date and reason.
- **Implementation before this change:** `backend/app/core/config.py` defines `SECRET_FIELDS` and a `_load_secret_files` validator that reads `<FIELD>_FILE` Docker secret files; `backend/app/core/secrets.py::read_secret()` falls back to the environment; `enforce_secret_policy()` fails closed in production on missing/placeholder values; `deployment_preflight.py` reports the same policy without exposing values. `.env` files are gitignored; no SOPS key material is committed.
- **Before OD-58 there was no Infisical integration:** no code, dependency, configuration or decision existed.
- **OD-51 §4.1 is separate:** the encrypted backend-only provider-key vault (`CryptoService`-encrypted AI provider API keys) is a runtime credential store, not the deployment secrets manager. This proposal does not touch it.

## 2. Why consider a change

**Benefits:** central rotation and audit trail, per-environment access control, no local encrypted files to distribute.

**Risks:** new runtime dependency and network path; a bootstrap credential that must itself be secured; third-party availability on startup; conflict with the local-first posture if hosted in Infisical Cloud; must preserve OD-10's rule that dev environments carry no production credentials.

## 3. Options — owner selects one

| Option | Description | Fit with locked decisions |
|--------|-------------|---------------------------|
| **A — Keep OD-07** | SOPS + Docker secrets unchanged; no Infisical | Fully compliant; zero change |
| **B — Self-hosted Infisical, dual-read** *(recommended if a change is wanted)* | Open-source self-hosted Infisical added as an extra source behind a flag; Docker secrets remain the authoritative fallback | Best fit with OD-10 / OD-15; no production credentials in dev; no third-party dependency |
| **C — Infisical Cloud, dual-read** | Same as B, but the control plane is hosted by Infisical | Requires explicit approval to send secret metadata and auth traffic to a third party |
| **D — Full migration** | Infisical becomes the sole source; SOPS/Docker secrets removed | Highest risk; needs a separate cutover decision and rollback plan |

**Owner selection (28 November 2026): Option C — Infisical Cloud, dual-read.** The draft recommended A/B; the owner selected C, which explicitly authorises secret metadata and authentication traffic to Infisical's hosted control plane.

## 4. Confirmed clauses (Option C)

| Clause | Proposed default | Owner decision |
|--------|------------------|----------------|
| Deployment | Infisical Cloud control plane (US `app.infisical.com` or EU `eu.infisical.com`); no self-hosted infrastructure; egress restricted to the allowlisted host | ✅ Confirmed — Option C (28 Nov 2026) |
| Environment mapping | One project; `dev` / `staging` / `production` mapped to `app_env`; production secrets never readable from dev (OD-10) | ✅ Accepted default (28 Nov 2026) |
| Secret scope | Only `SECRET_FIELDS` (deployment secrets); OD-51 provider-key vault stays local | ✅ Accepted default (28 Nov 2026) |
| Bootstrap auth | Machine identity client ID + secret injected as Docker secrets (`INFISICAL_CLIENT_ID_FILE`, `INFISICAL_CLIENT_SECRET_FILE`); never a literal in config or image | ✅ Accepted default (28 Nov 2026) |
| Precedence & fail-closed | Infisical queried first; Docker secret files (`<FIELD>_FILE`) then environment values are the fallback; `enforce_secret_policy()` unchanged; no value in logs or API; in production, no value from either source = startup abort | ✅ Accepted default (28 Nov 2026) |
| Fetch policy | Startup fetch into memory with bounded TTL refresh and last-known-good cache; refresh failure logs and keeps cache, never substitutes a placeholder | ✅ Accepted default (28 Nov 2026) |
| Feature flag | `secrets_backend=docker\|infisical`, default `docker`; enabled only after this decision | ✅ Accepted default (28 Nov 2026) |
| Network egress | Explicit allowlist of the Infisical host; no other outbound calls from the secret loader | ✅ Accepted default (28 Nov 2026) |
| Audit | Redacted status exposes secret names, source/status and error class — never values; no rotation-event audit is claimed by this decision | ✅ Accepted default (28 Nov 2026) |
| Reversal | Flag back to `docker` disables Infisical with no code change; removal follows change control | ✅ Accepted default (28 Nov 2026) |

## 5. Implementation gates (only after confirmation)

- Uses the already pinned `httpx` dependency (`httpx>=0.27.0` in `backend/pyproject.toml`, `httpx==0.29.0` in `backend/requirements.lock.txt`); no new third-party package was introduced.
- Add `secrets_backend` / `infisical_*` settings and extend `secrets.py::read_secret()` behind the flag, preserving the existing `SECRET_FIELDS` mapping and `read_secret()` abstraction.
- `deployment_preflight.py` reports source/availability without values.
- Unit tests: precedence rules, missing-secret and placeholder fail-closed, cache/refresh behaviour, and assurance that no secret value reaches logs or API responses.
- AGENTS.md gates: `ruff` clean, strict mypy ratchet 0 new errors, `pytest` 1092 passed at 66.48% coverage. OpenAPI/migration drift checks are unaffected (no API route or DB schema change).
- Same change updates `IAM_OWNER_DECISIONS.md` (amend OD-07 or record OD-58 with date and reason), `IAM_PRIVACY_AND_SECRETS.md`, and `ARCHITECTURE_INDEX.md`.
- **Implemented 28 November 2026:** `backend/app/core/infisical.py` (REST client, TTL cache, redacted status), `secrets_backend` settings, `read_secret()` integration, redacted preflight checks, and `backend/tests/test_infisical_secrets.py`. Verified: 1,092 tests pass, coverage 66.48%, ruff clean, mypy ratchet reports no new errors.

## 6. Preservation

This proposal does not change identity (OD-01), signing (OD-03), spending authority (OD-04/OD-25), protected-core rules (OD-11), approval mechanics (OD-19), dev/prod credential separation (OD-10), free-first replaceable tooling (OD-15), LiteLLM as gateway, the shared primary model (OD-38/OD-46), or the OD-51 §4.1 provider-key vault. It adds no frontend route and exposes no secret to the browser. OD-07 stays in force; OD-58 adds an optional source without replacing it.

## 7. Decision record

| Item | Decision |
|------|----------|
| OD-07 | ✅ **LOCKED — SOPS + Docker secrets** (unchanged baseline) |
| OD-58 | ✅ **CONFIRMED — Option C: Infisical Cloud, dual-read** (28 November 2026) |
| Infisical connection | ⚙️ **IMPLEMENTED, DEFAULT-OFF** — enable with `SECRETS_BACKEND=infisical` plus real machine-identity credentials and project ID |
| Paid/hosted model access | Unchanged — OD-57 remains proposed and unauthorised |
