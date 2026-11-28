# Creator email (SMTP) setup + operational Gmail status (28 November 2026)

Based on `docs/IAM_DEPLOYMENT_CONFIG.md`, `docs/IAM_COMMUNICATION_ARCHITECTURE.md` (OD-18/OD-19),
`backend/app/services/creator_email.py`, `backend/app/core/config.py`, `docker-compose.yml`
and a run of `python scripts/creator_email_preflight.py` on 28 November 2026.

## Creator approval email — Channel 2 (IAM domain)

### State before setup
- `CREATOR_PUBLIC_KEY` and `CREATOR_GATEWAY_SECRET` were already set in the host `.env`.
- `CREATOR_EMAIL_TRANSPORT` defaulted to `log` (safe): the package is recorded in
  `creator_email_outbox` but nothing leaves the host.
- Preflight failed on `CREATOR_EMAIL`, transport, `CREATOR_SMTP_HOST`,
  `CREATOR_SMTP_USER`, `CREATOR_SMTP_PASSWORD`.

### Changes made
- `docker-compose.yml`: forwarded `CREATOR_EMAIL_DOMAIN`, `CREATOR_EMAIL_FROM`,
  `CREATOR_SMTP_HOST`, `CREATOR_SMTP_PORT`, `CREATOR_SMTP_USER`,
  `CREATOR_SMTP_PASSWORD`, `CREATOR_SMTP_USE_TLS` to the `backend`,
  `creator-email-worker` and `iics-worker` services. Previously the compose file
  only forwarded `CREATOR_EMAIL`, `CREATOR_PUBLIC_KEY`, `CREATOR_EMAIL_TRANSPORT`
  and `CREATOR_GATEWAY_SECRET`, so SMTP settings in `.env` could never reach a
  container even when filled.
- `.env`: appended empty, clearly marked placeholders for the SMTP carrier.
  Transport deliberately stays `log` until real credentials are filled.

### Remaining manual steps (owner action — no secrets in chat or notes)
1. Fill in `.env`: `CREATOR_EMAIL` (a verified address on the IAM domain, e.g.
   `creator@iamagris.co.za`), optional `CREATOR_EMAIL_DOMAIN`, `CREATOR_EMAIL_FROM`,
   `CREATOR_SMTP_HOST`, `CREATOR_SMTP_PORT`, `CREATOR_SMTP_USER`,
   `CREATOR_SMTP_PASSWORD`, `CREATOR_SMTP_USE_TLS`.
2. Set `CREATOR_EMAIL_TRANSPORT=smtp` only after all of the above are filled.
3. Verify: `python scripts/creator_email_preflight.py` (exit 0 = carrier ready;
   never prints secret values). Also `python backend/scripts/deployment_preflight.py`.
4. Recreate the containers: `docker compose up -d --force-recreate`.
5. Confirm delivery with a real `POST /api/v1/creator/requests` and inspect
   `creator_email_outbox`; a signed decision still requires the external signer.

### Boundary
Email is the carrier, never the authority. A plain email reply does not grant
approval; authority remains the ED25519 signature over a one-time challenge.
`CREATOR_GATEWAY_SECRET` must be set or `/api/v1/creator/gateway/decide` is disabled.

## Operational Gmail — Channel 1 (Gmail)

- This is an account the owner creates and controls; no backend code creates it,
  sends from it, or stores its credentials. Grep of `backend/app` shows
  `operational_email` only as an allowed value of the `communication_audit.channel`
  constraint (`models/creatorapproval.py`, migration `0001_initial.py`).
- Manual setup: create/own the Gmail identity, enable 2FA, and if it will ever be
  used for SMTP use a Google App Password (not the account password). Keep those
  values outside the repository.
- **Gap:** there is no operational-email service, config block or route in the
  current code. Adding one would be a new capability beyond the frozen OD-18 spec
  and needs an owner decision before implementation. Do not confuse it with the
  Creator SMTP carrier above — OD-18 requires the channels to stay separate.

## Owner update (28 November 2026)

- **Channel 3 (private user communication):** the owner directed that this channel
  may **also be carried by email, but only when the user explicitly gives IAM their
  email address to chat there** (opt-in). This changes the frozen OD-18 / Doc 07
  wording, which currently describes Channel 3 as in-app only. It must be captured
  as a new owner decision/spec addendum before implementation — do not silently
  rewrite the frozen spec.
- **Operational Gmail (Channel 1):** the owner reports the Gmail account has been
  created. No credentials were supplied, and there is still no code that sends
  from it. It cannot double as the Creator carrier: OD-18 requires Channel 2 on
  IAM's own domain and `scripts/creator_email_preflight.py` rejects public mailboxes.
- **OD-59 / Document 39 are CONFIRMED** (owner confirmation 28 November 2026),
  recorded in `docs/IAM_OWNER_DECISIONS.md` and indexed in `docs/ARCHITECTURE_INDEX.md`.
  Chosen carrier: the IAM-domain address `chat@iamagris.co.za`
  (`USER_EMAIL_FROM`), distinct from `creator@` and the operational Gmail, which
  the owner confirmed is for IAM's autonomous use. Inbound via HMAC-protected
  forwarding webhook. **Implemented but default-off** (`USER_EMAIL_ENABLED=false`):
  service, models, migration 072, endpoints, container env pass-through and 11
  unit tests. Operator still supplies SMTP credentials and webhook secret.

## Related
- `docs/IAM_CREATOR_APPROVAL_SPEC.md`, `docs/IAM_API_CONTRACTS.md`
- `tools/rkie/notes/cloudflare-core-tunnel-deployment.md` (transport/identity gate only)
