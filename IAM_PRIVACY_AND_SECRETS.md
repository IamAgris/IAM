# Privacy, Secrets and Encryption

## Secret handling

- `backend/app/core/secrets.py` reads secrets from either the environment or a
  Docker secret file named `<ENV_VAR>_FILE`. Values are never logged.
- `enforce_secret_policy()` runs at backend startup. In `production`, placeholder
  values (`change-me…`) for app secret, session secret, Postgres password, LiteLLM
  key, S3 secret or encryption key abort startup.
- `deployment_preflight.py` reports the same policy without exposing values.

## Encryption at rest

- `backend/app/services/crypto_service.py` uses AES-GCM with `ENCRYPTION_KEY`.
- Visitor messages (`globalaccess`) and conversation messages (`conversations`)
  are encrypted on write and decrypted on read.
- Stored values are prefixed `enc:v1:`. Legacy plaintext rows remain readable, so
  enabling encryption does not lose existing data.
- Production requires a real base64 32-byte key; preflight flags a derived dev key.

## Data subject rights (OD-05)

Public endpoints under `/api/v1/access`:

- `GET /visitors/{visitor_token}/data` — inspect the visitor's sessions, messages,
  preferences, consents and memory permissions.
- `PATCH /visitors/{visitor_token}/data` — correct preferences and memory permissions.
- `DELETE /visitors/{visitor_token}` — delete all data held under the token.

All queries are scoped by the visitor token issued by the service. The service
generates an unpredictable token; any supplied token is only used to look up an
existing visitor, never trusted as a new identity.

## Verification

- 100 unit tests pass, including encryption round-trip, legacy plaintext reads,
  non-deterministic ciphertext and placeholder-key detection.
- Postgres integration check: visitor messages are stored with `enc:v1:` and are
  returned as plaintext through the inspect endpoint; correction and deletion pass.

## Remaining

- Redis-backed rate limiting for multi-replica deployments.
- Outbox dead-letter/alerting after repeated retry failures.
- Skill Runtime log streaming and per-skill invocation limits.
- Placeholder services (autonomy reasoning, TTS/VAD, video frames, research verification).
- `SAWarning`s in `worldmodel.py`.
