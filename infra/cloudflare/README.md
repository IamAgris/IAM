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
