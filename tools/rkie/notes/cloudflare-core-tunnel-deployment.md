# Cloudflare Tunnel + Access for the Core (deployed 28 November 2026)

Based on `infra/cloudflare/README.md`, `IAM_OWNER_DECISIONS.md` (OD-03/19/42)
and live `cf` CLI verification on 28 November 2026.

## Account and zone

- Account: `fcabe9d8ab19966326cfaed8cf33f23b` (OAuth profile `default`)
- Zone: `iamagris.co.za`, id `c6016d16e8e35c25c6d8f9548d66695f`, Free plan, active
- Before setup: no DNS records, tunnels, Access apps, Workers, D1 or KV; R2 not enabled.

## Resources created

| Resource | Value |
|---|---|
| Tunnel | `iam-core`, id `e89f13ea-7deb-4321-bd96-5d07bc6408c8`, remotely managed (`config_src: cloudflare`) |
| Tunnel ingress | `core.iamagris.co.za` → `http://localhost:8000`; catch-all `http_status:404`; config version 2 |
| Origin Access gate | `originRequest.access.required = true`, AUD `654c0da9e5e8926b45b4cfe88ddebac8e165d676346a8020511d23ab2c63fb39`, team `intellectualmainbrain` |
| DNS | `core.iamagris.co.za` CNAME → `<tunnel-id>.cfargotunnel.com`, proxied, id `bb085d952b0a229cb9fa1fef11e7d666` |
| Access app | `IAM Core`, id `09580be0-9136-47bd-a576-64c0aa578c30`, aud `654c0da9e5e8926b45b4cfe88ddebac8e165d676346a8020511d23ab2c63fb39`, type `self_hosted`, 24h session |
| Access policy | `Creator only`, id `2d91f239-4777-496b-aed9-65ad9061440f`, `allow` if email equals the Creator identity |
| Service Auth policy | `Creator CLI service token`, id `2f316c1c-a759-410a-92fe-479f12931138`, `non_identity`, token id below |
| Service token | `iam-creator-cli`, id `569b3434-8180-4657-a794-37faabe53780`, created 28 Nov 2026, expires 28 Nov 2027 |

Status after creation: tunnel `inactive` — no connector is running yet. The connector belongs on the
same host as the Core (Contabo VPS); the run token was written to a local file outside the repository
and must never be committed. The saved file contains the **raw token string**, not JSON.

`infra/cloudflare/setup-connector.sh` is the prepared copy-paste installer for the VPS. It installs
`cloudflared`, writes the token to `/etc/cloudflared/token` (mode 600), registers
`cloudflared-iam-core.service`, and starts it. It uses `cloudflared tunnel run --token-file` so the
token never appears in process arguments; no secret is stored in the repo. Bash syntax was checked on
28 November 2026.

## Important boundaries

- OD-42: Cloudflare is **transport only**, an identity gate, never authority. No signing or approval
  logic at the edge; the Core verifies all ED25519 challenges.
- Email OTP covers interactive browser access. Headless Creator CLI access uses the service token
  with `IAM_CF_ACCESS_CLIENT_ID` / `IAM_CF_ACCESS_CLIENT_SECRET`. Only the token ID/name belong in
  docs; the client ID and secret live in a local protected file and must never be committed.
- The account enforces strict service-token authentication: service-token selectors are rejected in
  `allow` policies (API error 12130). Service tokens must be in a separate `non_identity`
  (Service Auth) policy. First attempt to add it to `Creator only` failed with 400; the two-policy
  layout above is the working result.
- Independent MFA and device posture were intentionally not enabled on 28 November 2026.
  Independent MFA is an organisation-level setting (closed beta) and needs a registered
  security key; device posture would require WARP enrolment. Both would lock out the
  Creator if enabled before that preparation. The email OTP policy stays unchanged.
- The README's example uses a locally managed tunnel with a credentials file. This deployment uses a
  remotely managed tunnel with a run token instead; ingress is configured in Zero Trust / via `cf`.

## Useful commands

```powershell
cf tunnels list
cf tunnels config update <tunnel-id> --tunnel-config-ingress @ingress.json
cf dns records list -z iamagris.co.za
cf zero-trust access applications list
cf zero-trust access service-tokens list
cf tunnels token get <tunnel-id>    # secret — redirect to a protected file, never log it
```
