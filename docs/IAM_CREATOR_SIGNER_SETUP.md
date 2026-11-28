# Creator signer setup (OD-18 / OD-19)

Approval authority never lives inside IAM. It comes from an Ed25519 signature made by
the Creator's signer over a one-time challenge. Email/HTTP only carries the request
and the signed reply.

## Local development keypair

```powershell
python scripts/creator_signer_setup.py
```

The script writes `~/.config/iam/creator_ed25519.pem` with `0600` permissions and
prints only the **public** key. Copy that value into `CREATOR_PUBLIC_KEY`. The
private key is never printed and must never be committed or sent to IAM.

The example signer can then read the key from a file instead of an environment
variable, so the secret is not exposed in process listings:

```powershell
$env:IAM_CREATOR_SIGNING_KEY_FILE = "$HOME\.config\iam\creator_ed25519.pem"
python scripts/creator_signer_example.py "<challenge_hash>|<approved|rejected>"
```

For production, replace this with a hardware signer/HSM; keep the public key in
`CREATOR_PUBLIC_KEY` (or `CREATOR_PUBLIC_KEY_FILE`).

## Required configuration

| Setting | Purpose |
|---------|---------|
| `CREATOR_EMAIL` | Verified Creator address. **Still required** — a human must supply it. |
| `CREATOR_PUBLIC_KEY` | Ed25519 public key (base64 raw or PEM), now generated locally for development. |
| `CREATOR_SIGNER_ID` | Expected signer id; must match the signer used by the Creator CLI. |
| `CREATOR_GATEWAY_SECRET` | HMAC secret for the inbound signed-decision endpoint; generated locally. |
| `CREATOR_EMAIL_TRANSPORT` | `log` (safe default), `smtp`, or `http`. Nothing leaves the host in `log` mode. |

`python -m app.services.deployment_preflight.check_deployment` (or the API
readiness report) shows `creator_public_key`, `creator_gateway_secret` and
`creator_email_transport` as OK; `creator_email` remains a blocker until the
verified address is configured. That is intentionally a human step.

## Fail-closed rule

With no public key, no gateway secret, or no active signature over the exact
one-time challenge, every protected action is refused: delegation, paid
inference, skill invocation, paid search and model release/rollback.
