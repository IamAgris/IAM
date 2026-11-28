# Private Core access for the Creator CLI (Cloudflare)

Goal: the Creator CLI reaches IAM's Core API without exposing the Core to the
public internet. Cloudflare is **transport only** — it never grants authority;
authority remains the ED25519 signature over the one-time challenge (OD-03/19/42).

```
Creator CLI → Cloudflare Access → Cloudflare Tunnel → Core (localhost:8000)
```

## 1. Tunnel (outbound-only, no open ports)

Run `cloudflared` on the same host as the Core. Example `config.yml`:

```yaml
tunnel: <tunnel-uuid>
credentials-file: /etc/cloudflared/<tunnel-uuid>.json
ingress:
  - hostname: core.example.com
    service: http://localhost:8000
  - service: http_status:404
```

Route DNS to the tunnel and run the connector as a service. The Core needs no
inbound firewall rule. Verify current `cloudflared` install and plan limits via
official documentation — do not assume a free tier is unlimited (OD-15).

## 2. Access (identity gate)

Create a Cloudflare Access application for `core.example.com` with a policy that
allows only the Creator identity. Preferred: OIDC/email identity plus device
posture or WebAuthn/hardware key. A service token is acceptable for a headless
CLI but must be stored as a secret on the Creator machine, never in IAM.

Do **not** expose `/api/v1/creator/*` publicly without an Access policy. This is
an identity gate, not a Creator dashboard — OD-19 still applies.

## 3. CLI configuration

```bash
export IAM_CORE_URL=https://core.example.com
export IAM_TOKEN=<scoped IAM token>          # IAM's own auth, separate from Access
# Only when using an Access service token:
export IAM_CF_ACCESS_CLIENT_ID=<id>
export IAM_CF_ACCESS_CLIENT_SECRET=<secret>

python -m iam_sdk.creator_cli pending
python -m iam_sdk.creator_cli sign cr_... --approve --signer "python sign_with_key.py"
```

The SDK sends `CF-Access-Client-Id` / `CF-Access-Client-Secret` headers when both
variables are set, in addition to the normal IAM bearer token.

## 4. Boundaries

- Cloudflare terminates TLS at the edge; treat it as untrusted transport. All
  IAM responses remain untrusted until verified locally.
- No signing, approval or decision logic runs at the edge. The Core verifies
  every signature.
- Never place the Creator private key or the signing command in Cloudflare,
  a Worker, or any third-party environment.
- Keep the tunnel credentials and Access secrets out of Git (SOPS/Docker secrets, OD-07).
- Email remains optional notification only; this path does not depend on it.

## 5. Current deployment (28 November 2026)

The Cloudflare-side resources for `core.iamagris.co.za` are live in account
`fcabe9d8ab19966326cfaed8cf33f23b`:

- Tunnel `iam-core` (`e89f13ea-7deb-4321-bd96-5d07bc6408c8`), **remotely managed**.
  Ingress is configured in Zero Trust rather than in an origin `config.yml`, so the
  connector runs with `cloudflared tunnel run --token-file /etc/cloudflared/token`
  and needs no credentials file. The token is a secret: keep it on the Creator/VPS
  machine only, never in Git or in IAM, and never in the process arguments.
- Ingress: `core.iamagris.co.za` → `http://localhost:8000`, catch-all `http_status:404`.
  Config version 2 also sets `originRequest.access.required = true` with the app AUD
  (`654c0da9e5e8926b45b4cfe88ddebac8e165d676346a8020511d23ab2c63fb39`) and team
  `intellectualmainbrain`, so the tunnel rejects requests without a valid Access JWT
  before they reach the Core.
- Proxied CNAME `core.iamagris.co.za` → `<tunnel-id>.cfargotunnel.com`.
- Access application `IAM Core`, 24-hour session, with two policies:
  - `Creator only` — `allow` for the Creator email (one-time PIN), interactive use.
  - `Creator CLI service token` — `non_identity` (Service Auth) for service token
    `iam-creator-cli` (`569b3434-8180-4657-a794-37faabe53780`, expires 28 Nov 2027),
    headless CLI use. The account has strict service-token authentication enabled, so
    service tokens cannot be placed in an `allow` policy.

Independent MFA and device posture are deliberately **not enabled**. Access's
independent MFA is organisation-level (closed beta) and requires registering a
hardware key; device posture would require WARP enrolment. Enabling either without
that preparation would lock out the Creator. Add them only after the hardware key /
WARP enrolment is confirmed.

The tunnel is inactive until `cloudflared` is started on the same host as the Core
(Contabo VPS). For the headless Creator CLI set `IAM_CORE_URL`, `IAM_TOKEN`, plus
`IAM_CF_ACCESS_CLIENT_ID` and `IAM_CF_ACCESS_CLIENT_SECRET` from the protected token
file; never put those values in Git. See
`tools/rkie/notes/cloudflare-core-tunnel-deployment.md` for IDs and verification
commands (no secrets).

### 5.1 Start the connector on the VPS

`setup-connector.sh` in this directory installs `cloudflared`, writes the token to
`/etc/cloudflared/token` (mode 600), registers a systemd service, and starts it.
It contains no secrets.

1. Retrieve the run token on the machine that has the `cf` CLI and save it to a
   protected file (redirect — do not print it):

   ```powershell
   cf tunnels token get e89f13ea-7deb-4321-bd96-5d07bc6408c8 |
     Set-Content "$env:TEMP\iam-core-token.txt" -NoNewline
   ```

2. Copy `iam-core-token.txt` to the VPS by a secure channel, or just open the file
   locally and paste its single token string when the script prompts. The file holds
   the raw token (not JSON). Delete the local copy afterwards.

3. On the VPS, as root, on the same host where the Core listens on `localhost:8000`:

   ```bash
   sudo bash setup-connector.sh                 # prompts for the token
   # or: sudo bash setup-connector.sh /path/iam-core-token.txt
   ```

4. Verify:

   ```bash
   systemctl --no-pager status cloudflared-iam-core
   journalctl -u cloudflared-iam-core -n 30 --no-pager
   curl -sS http://localhost:8000/health
   curl -I https://core.iamagris.co.za/health    # expect an Access login redirect
   ```
