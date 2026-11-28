#!/usr/bin/env bash
# Install and start the iam-core Cloudflare Tunnel connector.
#
# Run this on the Contabo VPS, as root, on the SAME host where the IAM Core
# API listens on http://localhost:8000. No secret is stored in this script.
#
#   sudo bash setup-connector.sh                 # prompts for the token
#   sudo bash setup-connector.sh /path/token     # reads token from a local file
#
# The token is the single string saved outside the repo by:
#   cf tunnels token get e89f13ea-7deb-4321-bd96-5d07bc6408c8
# Treat it as a password. Never commit it.

set -euo pipefail

TUNNEL_ID="e89f13ea-7deb-4321-bd96-5d07bc6408c8"
TUNNEL_NAME="iam-core"
BIN="/usr/local/bin/cloudflared"
TOKEN_FILE="/etc/cloudflared/token"
UNIT="/etc/systemd/system/cloudflared-iam-core.service"
SERVICE="cloudflared-iam-core"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run as root (sudo -i or sudo bash $0)" >&2
  exit 1
fi

echo "==> 1/5: install cloudflared"
if [ ! -x "$BIN" ]; then
  case "$(uname -m)" in
    x86_64|amd64) ARCH="amd64" ;;
    aarch64|arm64) ARCH="arm64" ;;
    *) echo "ERROR: unsupported architecture $(uname -m)" >&2; exit 1 ;;
  esac
  echo "Downloading cloudflared-linux-${ARCH} ..."
  curl -fsSL --retry 3 \
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}" \
    -o "$BIN"
  chmod 0755 "$BIN"
else
  echo "Already installed: $BIN"
fi
"$BIN" --version

echo "==> 2/5: store the tunnel token (root-only, never in process args)"
install -d -m 0700 /etc/cloudflared
chmod 0700 /etc/cloudflared
if [ -s "$TOKEN_FILE" ]; then
  echo "Keeping existing token at $TOKEN_FILE (delete it first to replace)."
else
  if [ $# -ge 1 ]; then
    TOKEN="$(tr -d '\r\n' < "$1")"
  else
    read -rsp "Paste the iam-core tunnel token: " TOKEN
    echo
  fi
  if [ -z "$TOKEN" ]; then
    echo "ERROR: empty token" >&2
    exit 1
  fi
  printf '%s\n' "$TOKEN" > "$TOKEN_FILE"
  chmod 0600 "$TOKEN_FILE"
  chown root:root "$TOKEN_FILE"
  unset TOKEN
  echo "Saved $TOKEN_FILE (mode 600)."
fi

echo "==> 3/5: write the systemd unit"
cat > "$UNIT" <<UNIT_EOF
[Unit]
Description=Cloudflare Tunnel ${TUNNEL_NAME} (IAM Core)
Documentation=https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
ExecStart=${BIN} tunnel --no-autoupdate run --token-file ${TOKEN_FILE}
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT_EOF
chmod 0644 "$UNIT"

echo "==> 4/5: enable and start ${SERVICE}"
systemctl daemon-reload
systemctl enable --now "${SERVICE}.service"

echo "==> 5/5: status"
sleep 3
systemctl --no-pager status "${SERVICE}.service" || true
echo
echo "Connector target: tunnel ${TUNNEL_NAME} (${TUNNEL_ID}) -> http://localhost:8000"
echo "Verify from anywhere:"
echo "  curl -I https://core.iamagris.co.za/health     # should redirect to Access login"
echo "Verify on the VPS:"
echo "  journalctl -u ${SERVICE} -n 30 --no-pager"
echo "  curl -sS http://localhost:8000/health          # Core must answer locally"
