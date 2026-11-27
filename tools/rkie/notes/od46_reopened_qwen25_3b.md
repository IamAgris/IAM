# OD-46 reopened to Qwen2.5-3B (27 November 2026)

Owner direction: **qwen2.5:3b** is the shared primary local brain. The 26 Nov
Qwen2.5-Coder 3B choice in OD-46 is superseded; the coder remains an optional secondary.

## Files changed

| File | Change |
|------|--------|
| `backend/app/core/config.py` | `iam_primary_model=local-qwen-3b`, `iam_primary_local_tag=qwen2.5:3b`, adaptive tiers → `local-qwen-3b` |
| `docker-compose.yml` | Defaults for `IAM_PRIMARY_MODEL` / `IAM_PRIMARY_LOCAL_TAG` → qwen2.5:3b |
| `.env` | Explicit overrides updated (Compose/env beat code defaults) |
| `infra/litellm/config.yaml` | `local-qwen-3b` active; coder alias commented as optional secondary |
| `IAM_OWNER_DECISIONS.md` | OD-46 row, details and status note record the reopening |
| `IAM_FOUNDATION_MODEL_AND_INTELLIGENCE_SPEC.md` | Amendment + primary row + alias evidence |
| `IAM_PRIMARY_MODEL_UNIFICATION_SPEC.md` | Shared primary row, history and configuration |
| `ARCHITECTURE_INDEX.md` | Note reflects the reopening |

## Verification

- Runtime settings after recreate: `local-qwen-3b qwen2.5:3b local-qwen-3b`.
- LiteLLM `/v1/models`: only `local-qwen-3b` local alias active.
- Backend healthy; **725/725** unit tests pass.

## Gotcha

Code defaults alone were not enough: `.env` and `docker-compose.yml` explicitly set the old
model and overrode `config.py`. All three layers must agree.
