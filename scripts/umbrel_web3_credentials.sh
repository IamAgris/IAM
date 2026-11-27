#!/usr/bin/env bash
# Generate restricted IAM credentials ON THE UMBREL HOST.
#
# Safety:
#   - Never prints a macaroon, rune, certificate body or RPC password.
#   - Writes files with mode 0600 into a 0700 directory.
#   - Uses separate READ and WRITE credentials; no admin macaroon or unrestricted rune.
#   - Run this only after inspecting your container names and certificate paths with
#     `docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'`.
#
# Required environment:
#   SECRET_DIR=/secure/iam-web3-secrets
#   LND_CONTAINER=<umbrel lnd container name>
#   CLN_CONTAINER=<umbrel core-lightning container name>
# Optional:
#   LND_TLS_PATH=/root/.lnd/tls.cert
#   CLN_CA_PATH=/root/.lightning/ca.pem
#
# This script does not contact IAM and does not enable any feature flag.

set -euo pipefail

: "${SECRET_DIR:?SECRET_DIR is required}"
: "${LND_CONTAINER:?LND_CONTAINER is required}"
: "${CLN_CONTAINER:?CLN_CONTAINER is required}"

LND_TLS_PATH="${LND_TLS_PATH:-/root/.lnd/tls.cert}"
CLN_CA_PATH="${CLN_CA_PATH:-/root/.lightning/ca.pem}"

umask 077
mkdir -p "$SECRET_DIR"
chmod 700 "$SECRET_DIR"

say() { printf '%s\n' "$*"; }

# --- LND: read-only macaroon ---------------------------------------------------
# rpc permissions (not just REST paths) keep read and write separate.
docker exec "$LND_CONTAINER" lncli bakemacaroon \
  --save_to=/tmp/iam-lnd-read.macaroon \
  uri:/lnrpc.Lightning/GetInfo \
  uri:/lnrpc.Lightning/WalletBalance \
  uri:/lnrpc.Lightning/ChannelBalance \
  uri:/lnrpc.Lightning/ListChannels \
  uri:/lnrpc.Lightning/ListPeers \
  uri:/lnrpc.Lightning/ListInvoices \
  uri:/lnrpc.Lightning/ListPayments >/dev/null
docker cp "$LND_CONTAINER:/tmp/iam-lnd-read.macaroon" "$SECRET_DIR/lnd_readonly.macaroon" >/dev/null
docker exec "$LND_CONTAINER" sh -c 'command -v shred >/dev/null 2>&1 && shred -u /tmp/iam-lnd-read.macaroon || rm -f /tmp/iam-lnd-read.macaroon'

# --- LND: write-scoped macaroon (payments + invoices only) ---------------------
docker exec "$LND_CONTAINER" lncli bakemacaroon \
  --save_to=/tmp/iam-lnd-write.macaroon \
  uri:/invoicesrpc.Invoices/AddInvoice \
  uri:/lnrpc.Lightning/SendPaymentSync \
  uri:/lnrpc.Lightning/GetInfo >/dev/null
docker cp "$LND_CONTAINER:/tmp/iam-lnd-write.macaroon" "$SECRET_DIR/lnd_write.macaroon" >/dev/null
docker exec "$LND_CONTAINER" sh -c 'command -v shred >/dev/null 2>&1 && shred -u /tmp/iam-lnd-write.macaroon || rm -f /tmp/iam-lnd-write.macaroon'

# --- LND: TLS certificate ------------------------------------------------------
docker cp "$LND_CONTAINER:$LND_TLS_PATH" "$SECRET_DIR/lnd_tls.cert" >/dev/null

# --- CLN: read-only rune -------------------------------------------------------
# 'readonly' allows get*/list*/summary but excludes listdatastore.
docker exec "$CLN_CONTAINER" lightning-cli createrune null readonly \
  > "$SECRET_DIR/.cln-read.json"
python3 - "$SECRET_DIR/.cln-read.json" "$SECRET_DIR/cln_readonly.rune" <<'PY'
import json, pathlib, sys
payload = json.loads(pathlib.Path(sys.argv[1]).read_text())
pathlib.Path(sys.argv[2]).write_text(payload["rune"])
PY
{ command -v shred >/dev/null 2>&1 && shred -u "$SECRET_DIR/.cln-read.json"; } || rm -f "$SECRET_DIR/.cln-read.json"

# --- CLN: write-scoped rune (invoice + pay only) -------------------------------
docker exec "$CLN_CONTAINER" lightning-cli createrune -k "restrictions"='[[ "method=invoice", "method=pay", "method=getinfo", "method=listinvoices", "method=listpays" ]]' \
  > "$SECRET_DIR/.cln-write.json"
python3 - "$SECRET_DIR/.cln-write.json" "$SECRET_DIR/cln_write.rune" <<'PY'
import json, pathlib, sys
payload = json.loads(pathlib.Path(sys.argv[1]).read_text())
pathlib.Path(sys.argv[2]).write_text(payload["rune"])
PY
{ command -v shred >/dev/null 2>&1 && shred -u "$SECRET_DIR/.cln-write.json"; } || rm -f "$SECRET_DIR/.cln-write.json"

# --- CLN: CA certificate -------------------------------------------------------
docker cp "$CLN_CONTAINER:$CLN_CA_PATH" "$SECRET_DIR/cln_ca.pem" >/dev/null

chmod 600 "$SECRET_DIR"/*
say "Created restricted credential files in: $SECRET_DIR"
say "Files: lnd_readonly.macaroon, lnd_write.macaroon, lnd_tls.cert,"
say "       cln_readonly.rune, cln_write.rune, cln_ca.pem"
say "No credential values were printed. Verify with: ls -l $SECRET_DIR"
