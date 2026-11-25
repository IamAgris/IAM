# Deployment Configuration

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
2. `POST /api/v1/auth/bootstrap` with `X-Bootstrap-Key` to create the first
   admin credential.
3. Create a **user** credential for the open frontend and place it in
   `frontend/.env.local` as `IAM_USER_API_KEY`.
4. Never give the frontend an operator or admin key.

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
