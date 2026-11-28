#!/usr/bin/env bash
# GitHub Actions helper for the iam-core Cloudflare Tunnel connector.
# No self-hosted runner: this runs on a GitHub-hosted runner and uses SSH.
#
# Required environment (set from repository variables/secrets in the workflow):
#   DEPLOY_HOST, DEPLOY_USER, DEPLOY_SSH_KEY, DEPLOY_KNOWN_HOSTS
#   DEPLOY_PORT (optional, default 22)
#   CLOUDFLARE_TUNNEL_TOKEN (required only for action=deploy)
#
# Usage: bash infra/cloudflare/actions-deploy.sh deploy|verify

set -euo pipefail

ACTION="${1:-verify}"
CORE_URL="https://core.iamagris.co.za/health"
REMOTE_SCRIPT="/tmp/setup-connector.sh"
REMOTE_TOKEN="/tmp/iam-core-token"

for var in DEPLOY_HOST DEPLOY_USER DEPLOY_SSH_KEY DEPLOY_KNOWN_HOSTS; do
  if [ -z "${!var:-}" ]; then
    echo "ERROR: missing required environment variable $var" >&2
    exit 1
  fi
done

ssh_dir="$(mktemp -d)"
trap 'rm -rf "$ssh_dir"' EXIT
printf '%s\n' "$DEPLOY_SSH_KEY" > "$ssh_dir/deploy_key"
chmod 0600 "$ssh_dir/deploy_key"
printf '%s\n' "$DEPLOY_KNOWN_HOSTS" > "$ssh_dir/known_hosts"
chmod 0600 "$ssh_dir/known_hosts"

ssh_deploy() {
  ssh -i "$ssh_dir/deploy_key" -o IdentitiesOnly=yes \
    -p "${DEPLOY_PORT:-22}" -o BatchMode=yes -o StrictHostKeyChecking=yes \
    -o UserKnownHostsFile="$ssh_dir/known_hosts" \
    "$DEPLOY_USER@$DEPLOY_HOST" "$@"
}

scp_deploy() {
  scp -i "$ssh_dir/deploy_key" -o IdentitiesOnly=yes \
    -P "${DEPLOY_PORT:-22}" -o BatchMode=yes -o StrictHostKeyChecking=yes \
    -o UserKnownHostsFile="$ssh_dir/known_hosts" "$@"
}

if [ "$ACTION" = "deploy" ]; then
  if [ -z "${CLOUDFLARE_TUNNEL_TOKEN:-}" ]; then
    echo "ERROR: CLOUDFLARE_TUNNEL_TOKEN is required for deploy" >&2
    exit 1
  fi
  local_token="$ssh_dir/tunnel-token"
  printf '%s\n' "$CLOUDFLARE_TUNNEL_TOKEN" > "$local_token"
  chmod 0600 "$local_token"

  echo "==> copying connector installer and token"
  scp_deploy infra/cloudflare/setup-connector.sh \
    "$DEPLOY_USER@$DEPLOY_HOST:$REMOTE_SCRIPT"
  scp_deploy "$local_token" "$DEPLOY_USER@$DEPLOY_HOST:$REMOTE_TOKEN"

  echo "==> running installer on $DEPLOY_HOST"
  ssh_deploy 'chmod 0755 /tmp/setup-connector.sh && sudo bash /tmp/setup-connector.sh /tmp/iam-core-token; rc=$?; rm -f /tmp/iam-core-token /tmp/setup-connector.sh; exit $rc'
elif [ "$ACTION" = "verify" ]; then
  echo "==> verifying connector and Core"
  ssh_deploy 'systemctl --no-pager status cloudflared-iam-core || true; echo "--- recent logs ---"; journalctl -u cloudflared-iam-core -n 20 --no-pager; echo "--- local core health ---"; curl -sS -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000/health'
else
  echo "ERROR: action must be deploy or verify" >&2
  exit 1
fi

echo "==> checking edge Access redirect from the runner"
edge_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$CORE_URL")"
echo "edge $CORE_URL -> HTTP $edge_code (302 = Access login redirect, expected)"
if [ "$ACTION" = "verify" ] && [ "$edge_code" != "302" ]; then
  echo "ERROR: expected an Access redirect at the edge" >&2
  exit 1
fi
