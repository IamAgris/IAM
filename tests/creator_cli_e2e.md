# Creator CLI signed-decision path — end-to-end evidence

**Date:** 25 November 2026 · **Decision:** OD-42 (locked) · **Result:** PASS

This is a smoke test of the no-email authority path. It used a temporary ED25519
test keypair; the private key was deleted and the test public key/signer id were
removed from `.env` afterwards. Production requires the Creator's own hardware
signer public key (`CREATOR_PUBLIC_KEY`) and `CREATOR_SIGNER_ID`.

## Flow verified

1. `POST /api/v1/creator/requests` with `channel: creator_cli` — created request
   `cr_dda5d1307929fb88dd1d9284246382c9`, `delivery: not_applicable` (no email/outbox).
2. `python -m iam_sdk.creator_cli pending` — request visible.
3. `python -m iam_sdk.creator_cli challenge <id>` — returned `challenge_hash`, nonce,
   expiry, signer id and the two signable messages (`<hash>|approved`, `<hash>|rejected`).
4. `python -m iam_sdk.creator_cli sign <id> --approve --signer "python scripts/creator_signer_example.py" --dry-run`
   — produced a 88-character base64 signature without submitting.
5. Same command without `--dry-run` — signature verified by IAM; response:
   `status: approved`, `signature_verified: true`, `authorization_id` created.
6. `python -m iam_sdk.creator_cli show <id>` — persisted state confirmed.

## What this proves

- No email address or SMTP/HTTP email transport is required for a signed decision.
- Authority comes only from the verified ED25519 signature over the one-time challenge.
- The CLI, SDK `creator` section, non-email request channel and signed-decision gateway
  are operational together.

## Fixes made during the test

- `communication_audit` check constraint widened to allow `creator_cli`,
  `creator_webhook`, `creator_node` and `creator_file` (model + migration 016).
- Creator settings (`CREATOR_EMAIL`, `CREATOR_PUBLIC_KEY`, `CREATOR_SIGNER_ID`,
  `CREATOR_EMAIL_TRANSPORT`, `CREATOR_GATEWAY_SECRET`) added to `docker-compose.yml`
  backend environment — previously they never reached the container.
- Duplicate `IAM_BOOTSTRAP_API_KEY` lines in `.env` deduplicated.

## Reference signer

`scripts/creator_signer_example.py` is a template only. Replace it with a command backed
by your hardware key/HSM. It reads `IAM_CREATOR_SIGNING_KEY` from the environment and
signs `sys.argv[-1]`; it never contacts IAM and stores no key.
