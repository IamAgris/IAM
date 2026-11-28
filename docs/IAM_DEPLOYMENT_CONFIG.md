# Deployment Configuration

## Docker secrets

Secret settings can be supplied as files instead of literal environment values:
set `<FIELD>_FILE` to a mounted secret path (for example
`APP_SECRET_KEY_FILE=/run/secrets/app_secret_key`). `Settings` loads these at
startup; plain environment values remain the fallback. Secret values are never
logged or returned by any endpoint.

## Optional Infisical Cloud source (OD-58)

Docker secrets stay the default. To read deployment secrets from Infisical Cloud
instead, set `SECRETS_BACKEND=infisical` and supply:

- `INFISICAL_PROJECT_ID` — the Infisical project ID.
- `INFISICAL_CLIENT_ID_FILE` / `INFISICAL_CLIENT_SECRET_FILE` — mounted Docker
  secrets holding the machine identity's Universal Auth credentials. Plain
  `INFISICAL_CLIENT_ID` / `INFISICAL_CLIENT_SECRET` environment values are also
  accepted, but Docker secret files are preferred.
- `INFISICAL_SITE_URL` (default `https://app.infisical.com`),
  `INFISICAL_ALLOWED_HOSTS` (default `app.infisical.com,eu.infisical.com`),
  `INFISICAL_ENVIRONMENT` (default derived from `APP_ENV`: dev/staging/prod),
  plus optional cache, refresh-margin and timeout settings.

Infisical is queried first; Docker secret files and environment values remain
the fallback. Values are cached in memory with a bounded TTL; fetch failures
keep the last-known-good cache. Only `SECRET_FIELDS` names are read. The
production fail-closed policy is unchanged, and no value is logged or returned
by any endpoint. Disable by setting `SECRETS_BACKEND=docker`.

## Preflight

Run this before enabling any external integration:

```bash
cd backend
python scripts/deployment_preflight.py
```

Exit code 1 means blockers remain. The same report is available at
`GET /api/v1/deployment/preflight` with an admin credential. It returns names
and status only — never secret values.

## Required for signed Creator approval

1. `CREATOR_EMAIL` — the verified Creator address on IAM's domain.
2. `CREATOR_PUBLIC_KEY` — ED25519 **public** key of the external signer (PEM or
   base64 raw). IAM never holds the private key.
3. `CREATOR_GATEWAY_SECRET` — HMAC secret for inbound decisions. An empty value
   disables `/api/v1/creator/gateway/decide`.
4. Choose a delivery transport:
   - `CREATOR_EMAIL_TRANSPORT=log` (default) — records the package, sends nothing.
   - `smtp` — set `CREATOR_SMTP_HOST`, `CREATOR_SMTP_PORT`, `CREATOR_SMTP_USER`,
     `CREATOR_EMAIL_FROM` and `CREATOR_SMTP_PASSWORD`.
   - `http` — set `CREATOR_EMAIL_HTTP_URL` and optionally
     `CREATOR_EMAIL_HTTP_TOKEN`.

## API credentials

1. Set `IAM_BOOTSTRAP_API_KEY`.
2. Run `python backend/scripts/bootstrap_credentials.py`. It creates the first
   admin credential, then a `user` credential, and writes only the user key to
   `frontend/.env.local`. Secrets are never printed.
3. Never give the frontend an operator or admin key.

## Proxy boundary

`infra/gateway/nginx.conf` restricts `/api/v1/creator/gateway/decision` to the
email/signer gateway network and `/api/v1/auth/bootstrap` to the operator
network. Add the real CIDRs before deploying; everything else passes through to
the open user frontend.

## Authorized ARTEX lab

`infra/artex-lab/docker-compose.yml` is a loopback-only template for a lab you
own or are explicitly authorized to test. Set `ARTEX_IMAGE` to a verified fork
image, keep `ARTEX_DRY_RUN=true` initially, and never expose ports 8787/8788
publicly.

## Media and reasoning

- `ffmpeg` is installed in the backend image; `VISION_FFMPEG_PATH` defaults to it.
- Set `VOICE_TTS_URL` (and optionally `VOICE_TTS_API_KEY`) for speech output.
- LiteLLM is already wired in `docker-compose.yml` for autonomy and vision.

## Optional: Skill Runtime

- `SKILL_RUNTIME_ENABLED=false` and `SKILL_RUNTIME_ADAPTER=stub` by default.
- To enable real execution: `SKILL_RUNTIME_ADAPTER=docker`, choose a trusted
  image, keep the sandbox limits, and run
  `python tests/docker_adapter_lab_check.py` first.

## Optional: ARTEX

- Keep `ARTEX_ENABLED=false` until an authorized lab exists.
- Endpoint must be loopback (`http://127.0.0.1:8787`) unless private networking
  is explicitly opted into.
- Set `ARTEX_MCP_TOKEN` environment variable and keep `ARTEX_DRY_RUN=true` for
  the first runs.

## Boundaries

No Creator UI, no operator/admin UI. The frontend is open and user-only; every
non-user action goes through the signed email flow or a scoped backend credential.

## Related

- `IAM_CREATOR_APPROVAL_SPEC.md`
- `IAM_API_AUTH_SPEC.md`
- `IAM_SKILL_RUNTIME_SPEC.md`
- `IAM_ARTEX_INTEGRATION_SPEC.md`
- `IAM_CI_AND_WORKERS.md`
