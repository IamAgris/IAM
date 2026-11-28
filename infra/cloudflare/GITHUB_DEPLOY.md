# Deploy the Cloudflare connector from GitHub Actions

`.github/workflows/deploy-cloudflare-connector.yml` runs manually (`workflow_dispatch`)
on a GitHub-hosted runner. It copies `setup-connector.sh` and the tunnel token to the
target server over SSH and runs the installer there. **No self-hosted runner is used.**

Nothing in this directory contains a secret. All credentials come from repository
variables/secrets.

## Repository configuration

| Kind | Name | Purpose |
|---|---|---|
| Variable | `DEPLOY_HOST` | Hostname/IP of the server that runs the IAM Core API |
| Variable | `DEPLOY_USER` | SSH login user on that server |
| Variable | `DEPLOY_PORT` | Optional SSH port, default `22` |
| Secret | `DEPLOY_SSH_KEY` | Private key (OpenSSH format) for `DEPLOY_USER` |
| Secret | `DEPLOY_KNOWN_HOSTS` | The single `ssh-keyscan` line for `DEPLOY_HOST` |
| Secret | `CLOUDFLARE_TUNNEL_TOKEN` | `iam-core` run token; needed only for `deploy` |

The workflow uses `StrictHostKeyChecking=yes` with `DEPLOY_KNOWN_HOSTS`, so it will
refuse a changed host key instead of silently accepting a man-in-the-middle.

## Preparing the values

1. Add the runner's **public** key to `DEPLOY_USER`'s `~/.ssh/authorized_keys` on the
   server. Keep the private key as the `DEPLOY_SSH_KEY` secret.
2. Record the server's host key out-of-band, then store it as `DEPLOY_KNOWN_HOSTS`:

   ```bash
   ssh-keyscan -t ed25519 <host>
   # verify the fingerprint via the provider console before saving the line
   ```

3. Retrieve the tunnel token on a machine with the `cf` CLI and store it as the
   `CLOUDFLARE_TUNNEL_TOKEN` secret. Do not print or commit it:

   ```powershell
   cf tunnels token get e89f13ea-7deb-4321-bd96-5d07bc6408c8 |
     Set-Content "$env:TEMP\iam-core-token.txt" -NoNewline
   ```

## Running

In the Actions tab, run **Deploy IAM Core Cloudflare connector**:

- `deploy` — uploads and runs the installer, enabling `cloudflared-iam-core.service`
- `verify` — checks the service, recent logs, local Core health, and the edge redirect

Expected edge result: `curl -I https://core.iamagris.co.za/health` returns **302** to
the Cloudflare Access login. Local result on the server: `http://localhost:8000/health`
returns 200.

## Scope note

The workflow manages the connector only. Cloudflare-side resources (DNS, Access app,
policies, service token, tunnel ingress) are created with `cf` and documented in
`tools/rkie/notes/cloudflare-core-tunnel-deployment.md`. The target server had not been
chosen when this workflow was written, so the variables/secrets are intentionally
unset until the owner provides it.
