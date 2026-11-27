#!/usr/bin/env bash
# Read-only Umbrel inspection for the Web3/node activation runbook.
#
# Collects: OS, kernel, Docker version, container names/images/status/ports,
# host IPs and Tailscale status. Never reads env files, credentials, certificates
# or wallet data. Safe to paste the generated report into a chat.
#
# Run ON the Umbrel host:
#   bash umbrel_inspect.sh
# Then send the generated umbrel-web3-inspection.txt to the operator.

set -uo pipefail

REPORT="umbrel-web3-inspection.txt"
umask 077

{
  echo "# Umbrel inspection — Web3/node activation"
  echo "generated_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "## OS"
  cat /etc/os-release 2>/dev/null || echo "unavailable"
  echo
  echo "## Kernel"
  uname -a 2>/dev/null || echo "unavailable"
  echo
  echo "## Hostname"
  hostname 2>/dev/null || echo "unavailable"
  echo
  echo "## Docker version"
  docker version 2>&1 || echo "unavailable"
  echo
  echo "## Containers (names, images, status, published ports)"
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>&1 || echo "unavailable"
  echo
  echo "## Host IPs"
  hostname -I 2>/dev/null || echo "unavailable"
  echo
  echo "## Tailscale"
  if command -v tailscale >/dev/null 2>&1; then
    tailscale status 2>&1 || echo "tailscale status unavailable"
    echo "tailscale_ip=$(tailscale ip -4 2>/dev/null || echo none)"
  else
    echo "tailscale not installed on this host"
  fi
} > "$REPORT"

chmod 600 "$REPORT"
echo "Wrote $REPORT (read-only, no credential values)."
grep -E '^(PRETTY_NAME=|tailscale_ip=)' "$REPORT" || true
echo "Container rows: $(grep -c '^\S' "$REPORT" || true) (report has full list)."
